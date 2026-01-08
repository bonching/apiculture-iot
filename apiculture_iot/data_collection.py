#!/usr/bin/env python3

import sys

from flask import Flask, request
from flask_socketio import SocketIO, emit
from picamera2 import Picamera2
import requests
import threading
import time
import os
from datetime import datetime
from gpiozero import AngularServo
import board
import adafruit_bme280.basic as adafruit_bme280


DATA_COLLECTION_INTERVAL = 60*5
IMAGE_API_URL = 'http://192.168.68.106:8081/api/images'
SENSOR_DATE_API_URL = 'http://192.168.68.106:8081/api/sensor-data'

#GPIO Configuration
SERVO_PIN = 18

# BME280 Configuration
BME280_I2C_ADDRESS = 0x76 # Default I2C address for BME280 (use 0x77 if needed)

# Storage directories
PHOTO_DIR = "/home/apiculture/photos"
VIDEO_DIR = "/home/apiculture/videos"

app = Flask(__name__)
app.config['SECRET_KEY'] = 'apiculture-iot-secret-key'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Initialize camera
try:
    camera = Picamera2()
    camera_available = True
except Exception as e:
    print(f"Error initializing camera: {e}")
    camera = None
    camera_available = False

# Initialize servo for data collection
try:
    data_collection_servo = AngularServo(SERVO_PIN, min_angle=-90, max_angle=90)
    servo_available = True
    print("Servo initialized on GPIO PIN: ", SERVO_PIN)
except Exception as e:
    print(f"Error initializing servo: {e}")
    data_collection_servo = None
    servo_available = False

os.makedirs(PHOTO_DIR, exist_ok=True)
os.makedirs(VIDEO_DIR, exist_ok=True)

camera_state = {
    'recording': False,
    'last_photo': None,
    'last_video': None,
    'video_start_time': None
}

# Lock for thread-safe operations
state_lock = threading.Lock()

# Connected clients tracking
connected_clients = set()

# Helper functions to broadcast status updates to all clients
def broadcast_status_update(device, status):
    """Broadcast status update to all connected clients"""
    socketio.emit('status:update', {
        'device': device,
        'status': status,
        'timestamp': time.strftime("%Y-%m-%d %H:%M:%S")
    }, namespace='/')



# ============= Websocket Connection Handlers =============
@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    client_id = request.sid

    connected_clients.add(client_id)
    print(f"Client connected: {client_id} (Total clients: {len(connected_clients)})")

    # Send welcome message with current device states
    emit('connected', {
        'success': True,
        'message': 'Connected to Apiculture IoT Control System',
        'client_id': client_id,
        'devices': {
            'camera': camera_state.copy()
        },
        'device_availability': {
            'camera': 'available' if camera_available else 'unavailable'
        }
    })


@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    client_id = request.sid
    connected_clients.remove(client_id)
    print(f"Client disconnected: {client_id} (Total clients: {len(connected_clients)})")


@socketio.on('get:status')
def handle_get_status():
    """Send all device statuses to requesting clients"""
    with state_lock:
        emit('status:all', {
            'success': True,
            'devices': {
                'camera': camera_state.copy()
            }
        })


@socketio.on('get:health')
def handle_get_health():
    """Health check - return system status"""
    emit('health:response', {
        'success': True,
        'message': 'IoT Control Websocket API is running',
        'timestamp': time.strftime("%Y-%m-%d %H:%M:%S"),
        'connected_clients': len(connected_clients),
        'devices': {
            'camera': 'available' if camera_available else 'unavailable'
        }
    })


# ============= Camera =============

@socketio.on('camera:capture')
def handle_camera_capture(data):
    """Capture a photo"""
    if not camera_available:
        emit('error', {'message': 'Camera is not available', 'device': 'camera'})
        return

    try:
        data = data or {}
        filename = data.get('filename', f'photo_{datetime.now().strftime("%Y%m%d_%H%M%S")}.jpg')

        if not filename.endswith(('.jpg', '.jpeg', '.png')):
            filename += '.jpg'

        filepath = os.path.join(PHOTO_DIR, filename)

        # Configure and capture
        camera.start()
        time.sleep(2)
        camera.capture_file(filepath)
        camera.stop()

        with open(filepath, 'rb') as image_file:
            # Create a dictionary for the files to be sent, using the new filename
            files = {'image': (filename, image_file, 'image/jpeg')}
            data = {'context': 'data_collection'}

            try:
                # Send the POST request
                response = requests.post(IMAGE_API_URL, files=files, data=data)

                # Check the response
                if response.status_code == 200:
                    print("Image uploaded successfully!")
                    print("Response:", response.text)
                else:
                    print(f"Failed to upload image. Status code: {response.status_code}")
                    print("Response:", response.text)

            except requests.exceptions.RequestException as e:
                print(f"An error occurred: {e}")

        with state_lock:
            camera_state['last_photo'] = filepath

        response = {
            'success': True,
            'filename': filename,
            'filepath': filepath,
            'message': f'Photo captured successfully'
        }

        emit('camera:response', response)
        broadcast_status_update('camera', camera_state.copy())

    except Exception as e:
        emit('error', {'message': str(e), 'device': 'camera'})


@socketio.on('camera:video')
def handle_camera_video(data):
    """Start/stop video recording"""
    if not camera_available:
        emit('error', {'message': 'Camera is not available', 'device': 'camera'})
        return

    try:
        if not data or 'action' not in data:
            emit('error', {'message': 'Missing action parameter', 'device': 'camera'})
            return

        action = data['action'].lower()

        if action == 'start':
            if camera_state['recording']:
                emit('error', {'message': 'Camera is already recording', 'device': 'camera'})
                return

            duration = data.get('duration', None)
            filename = data.get('filename', f'video_{datetime.now().strftime("%Y%m%d_%H%M%S")}.h264')

            if not filename.endswith(('.h264', '.mp4')):
                filename += '.h264'

            filepath = os.path.join(VIDEO_DIR, filename)

            # Start recording
            camera.start_recording(filepath)

            with state_lock:
                camera_state['recording'] = True
                camera_state['last_video'] = filepath
                camera_state['video_start_time'] = time.time()

            # Auto-stop if duration is specified
            if duration and duration > 0:
                def auto_stop_video():
                    time.sleep(float(duration))
                    if camera_state['recording']:
                        camera.stop_recording()
                        with state_lock:
                            camera_state['recording'] = False
                        broadcast_status_update('camera', camera_state.copy())

                threading.Thread(target=auto_stop_video, daemon=True).start()
                response = {
                    'success': True,
                    'filename': filename,
                    'duration': duration,
                    'message': f'Video recording started for {duration} seconds'
                }
            else:
                response = {
                    'success': True,
                    'filename': filename,
                    'message': f'Video recording started'
                }

            emit('camera:response', response)
            broadcast_status_update('camera', camera_state.copy())

        elif action == 'stop':
            if not camera_state['recording']:
                emit('error', {'message': 'Camera is not recording', 'device': 'camera'})
                return

            camera.stop_recording()

            with state_lock:
                camera_state['recording'] = False

            response = {
                'success': True,
                'message': 'Video recording stopped'
            }

            emit('camera:response', response)
            broadcast_status_update('camera', camera_state.copy())

        else:
            emit('error', {'message': f'Invalid action: {action}, action must be start or stop', 'device': 'camera'})

    except Exception as e:
        emit('error', {'message': str(e), 'device': 'camera'})


def cleanup():
    """Cleanup function to stop all devices on exit"""
    if camera_available and camera_state['recording']:
        try:
            camera.stop_recording()
        except:
            pass

    if servo_available:
        try:
            data_collection_servo.angle = 0 # Return to neutral position
            time.sleep(0.5)
            data_collection_servo.close()
        except:
            pass

    print('All devices stopped and cleaned up')


# ============= data collection =============
def execute_data_collection():
    """
    Execute data collection process:
    1. Move servo to slide-open the sensor cover
    2. Collect BME280 sensor data and post to API
    3. Capture image and post to API
    """
    while True:
        try:
            time.sleep(DATA_COLLECTION_INTERVAL)
            print("=" * 60)
            print("Data collection interval reached, executing data collection...")
            print("=" * 60)

            # Step 1: Move the servo
            if servo_available:
                try:
                    print("Step 1: Moving servo to slide-open the sensor cover...")
                    data_collection_servo.angle = 90
                    time.sleep(2)
                    print("Servo positioned at 90 degrees")
                except Exception as e:
                    print(f"Error moving servo: {e}")
            else:
                print("Servo not available, skipping servo movement...")

            # Step 2: Collect BME sensor data and post to API
            try:
                print("\nStep 2: Collecting BME280 sensor data...")

                # Initialize I2C bus
                try:
                    i2c = board.I2C()
                except Exception as e:
                    print(f"Failed to initialize I2C: {e}")
                    raise

                # Initialize BME280 sensor
                try:
                    sensor = adafruit_bme280.Adafruit_BME280_I2C(i2c, address=BME280_I2C_ADDRESS)
                except Exception as e:
                    print(f"Failed to initialize BME280: {e}")
                    print("Check I2C connections and address (0x76 or 0x77)")
                    raise

                # Read sensor data
                temperature = round(sensor.temperature, 2)
                humidity = round(sensor.humidity, 2)
                pressure = round(sensor.pressure, 2)

                print(f"Temperature: {temperature} C")
                print(f"Humidity: {humidity}%")
                print(f"Pressure: {pressure} hPa")

                # Prepare sensor data payload
                payload = {
                    'temperature': temperature,
                    'humidity': humidity,
                    'pressure': pressure
                }

                # Post sensor data to API
                try:
                    response = requests.post(SENSOR_DATE_API_URL, json=payload)
                    if response.status_code == 200:
                        print("Sensor data posted successfully!")
                        print("Response:", response.text)
                    else:
                        print(f"Failed to post sensor data. Status code: {response.status_code}")
                        print("Response:", response.text)
                except requests.exceptions.RequestException as e:
                    print(f"An error occurred: {e}")

            except Exception as e:
                print(f"Error collecting sensor data: {e}")

            # Step 3: Capture image and post to API
            if camera_available:
                try:
                    print("\nStep 3: Capturing image...")
                    handle_camera_capture({'context': 'data_collection'})
                except Exception as e:
                    print(f"Error capturing image: {e}")
            else:
                print("Camera not available, skipping image capture...")

            # Return servo to neutral position
            if servo_available:
                try:
                    print("\nStep 4: Returning servo to neutral position...")
                    data_collection_servo.angle = 0 # Return to neutral position
                    time.sleep(1)
                    print("Servo returned to neutral position")
                except Exception as e:
                    print(f"Error returning servo to neutral position: {e}")

            print("Data collection completed successfully!")
            print("=" * 60)

        except Exception as e:
            print(f"Error executing data collection: {e}")
            # Continue running despite error
            pass



if __name__ == '__main__':
    import atexit
    import signal

    atexit.register(cleanup)

    def signal_handler(signal, frame):
        print('Shutting down...')
        cleanup()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    print("\n\n\n")
    print("=" * 60)
    print("Starting Apiculture IoT Websocket Control API...")
    print("=" * 60)
    print("\n\n\n")

    # Execute data collection in a fixed interval (start as background thread)
    threading.Thread(target=execute_data_collection, daemon=True).start()

    socketio.run(app, host='0.0.0.0', port=5000, debug=False, allow_unsafe_werkzeug=True)
