#!/usr/bin/env python3
import random
import sys
import traceback

from flask import Flask, request
from flask_socketio import SocketIO, emit
from picamera2 import Picamera2
import requests
import threading
import time
import os
from datetime import datetime, timezone
from gpiozero import AngularServo
import board
import adafruit_bme280.basic as adafruit_bme280

from apiculture_iot.util.app_util import AppUtil
from apiculture_iot.util.config import DATA_COLLECTION_METRICS, API_HOST, API_PORT, BEEHIVE_ID, \
    DEFENSE_CAMERA_SENSOR_ID, BEE_COUNTER_CAMERA_SENSOR_ID

util = AppUtil()

from apiculture_iot.util.mongo_client import ApicultureMongoClient
mongo = ApicultureMongoClient()

import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s:%(lineno)d - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('apiculture-iot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('data_collection')
logger.setLevel(logging.INFO)


DATA_COLLECTION_INTERVAL = 60*1
IMAGE_API_URL = f'http://{API_HOST}:{API_PORT}/api/images'
SENSOR_DATA_API_URL = f'http://{API_HOST}:{API_PORT}/api/metrics'

#GPIO Configuration
SERVO_PIN = 18

# BME280 Configuration
BME280_I2C_ADDRESS = 0x77 # Default I2C address for BME280 (use 0x77 if needed)

# Storage directories
PHOTO_DIR = "/home/apiculture/photos"
VIDEO_DIR = "/home/apiculture/videos"

# Fallback image path (relative to the project root)
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
FALLBACK_IMAGE_PATH = os.path.join(PROJECT_ROOT, 'images', 'honeycomb.jpg')

app = Flask(__name__)
app.config['SECRET_KEY'] = 'apiculture-iot-secret-key'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Initialize camera
try:
    camera = Picamera2()
    camera_available = True
except Exception as e:
    logger.error(f"Error initializing camera: {e}")
    camera = None
    camera_available = False

# Initialize servo for data collection
try:
    data_collection_servo = AngularServo(SERVO_PIN, min_angle=-90, max_angle=90)
    servo_available = True
    logger.info(f"Servo initialized on GPIO PIN: {SERVO_PIN}")
except Exception as e:
    logger.error(f"Error initializing servo: {e}")
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
    logger.info(f"Client connected: {client_id} (Total clients: {len(connected_clients)})")

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
    logger.info(f"Client disconnected: {client_id} (Total clients: {len(connected_clients)})")


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

    try:
        data = data or {}
        filename = data.get('filename', f'data_collection_{datetime.now().strftime("%Y%m%d_%H%M%S")}.jpg')

        if not filename.endswith(('.jpg', '.jpeg', '.png')):
            filename += '.jpg'

        filepath = os.path.join(PHOTO_DIR, filename)

        # Configure and capture
        if camera_available:
            camera.start()
            time.sleep(2)
            camera.capture_file(filepath)
            camera.stop()
            logger.info(f"Photo captured from camera: {filepath}")
        else:
            # Use random fallback image from bees folder when camera is unavailable
            logger.warning("Camera is unavailable, using random fallback image from bees folder")
            bees_dir = os.path.join(PROJECT_ROOT, 'images', 'bees')

            if os.path.exists(bees_dir):
                # Get all image files from bees directory
                import shutil
                image_files = [f for f in os.listdir(bees_dir) if f.lower().endswith(('.jpg', '.jpeg', '.png'))]

                if image_files:
                    # Select a random image
                    random_image = random.choice(image_files)
                    random_image_path = os.path.join(bees_dir, random_image)

                    # Copy the image to the photos directory
                    shutil.copy2(random_image_path, filepath)
                    logger.info(f"Random fallback image '{random_image}' copied to: {filepath}")
                else:
                    logger.error(f"No images found in bees directory: {bees_dir}")
                    emit('error', {'message': f"No images found in bees directory: {bees_dir}", 'device': 'camera'})
                    return
            else:
                logger.error(f"Honeypots directory not found at: {bees_dir}")
                emit('error', {'message': f"Honeypots directory not found at: {bees_dir}", 'device': 'camera'})
                return

        client_id = data.get('client_id')

        with open(filepath, 'rb') as image_file:
            # Create a dictionary for the files to be sent, using the new filename
            files = {'image': (filename, image_file, 'image/jpeg')}
            data = {'context': 'harvest', 'sensorId': DEFENSE_CAMERA_SENSOR_ID} if 'context' not in data else data
            logger.info(f"data: {data}")

            try:
                # Send the POST request
                response = requests.post(IMAGE_API_URL, files=files, data=data)

                # Check the response
                if response.status_code == 200 or response.status_code == 201:
                    logger.info("Image uploaded successfully!")
                    logger.info(f"Response: {response.text}")

                    if data.get('context') == 'data_collection':
                        data_type = mongo.data_types_collection.find_one({'sensor_id': BEE_COUNTER_CAMERA_SENSOR_ID, 'data_type': 'bee_count'})
                        bee_count_data = [
                            {
                                'datetime': datetime.now(timezone.utc).isoformat(timespec='milliseconds'),
                                'dataTypeId': util.objectid_to_str(data_type['_id']),
                                'value': response.text['bee_count']['count'],
                                'imageId': response.text['imageId']
                            }
                        ]
                        logger.info(f"Bee count from image analysis: {str(bee_count_data)}")
                        response = requests.post(f'http://{API_HOST}:{API_PORT}/api/metrics', json=bee_count_data)
                        logger.info(response.json())
                else:
                    logger.info(f"Failed to upload image. Status code: {response.status_code}")
                    logger.info(f"Response: {response.text}")

            except requests.exceptions.RequestException as e:
                logger.error(f"An error occurred: {e}")
                traceback.print_exc()

        with state_lock:
            camera_state['last_photo'] = filepath

        response = {
            'success': True,
            'filename': filename,
            'filepath': filepath,
            'message': f'Photo captured successfully' if camera_available else 'Fallback image used (camera is unavailable)'
        }

        if data.get('context') == 'harvest':
            emit('camera:response', response)
            broadcast_status_update('camera', camera_state.copy())

    except Exception as e:
        traceback.print_exc()
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
        traceback.print_exc()
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

    logger.info('All devices stopped and cleaned up')


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
            logger.info("=" * 60)
            logger.info("Data collection interval reached, executing data collection...")
            logger.info("=" * 60)

            # Step 1: Move the servo
            if servo_available:
                try:
                    logger.info("Step 1: Moving servo to slide-open the sensor cover...")
                    data_collection_servo.angle = 90
                    time.sleep(2)
                    logger.info("Servo positioned at 90 degrees")
                except Exception as e:
                    logger.error(f"Error moving servo: {e}")
            else:
                logger.info("Servo not available, skipping servo movement...")

            # Step 2: Collect BME sensor data and post to API
            try:
                logger.info("\nStep 2: Collecting BME280 sensor data...")

                # Initialize I2C bus
                try:
                    i2c = board.I2C()

                    # Initialize BME280 sensor
                    try:
                        sensor = adafruit_bme280.Adafruit_BME280_I2C(i2c, address=BME280_I2C_ADDRESS)

                        # Read sensor data
                        temperature = round(sensor.temperature, 2)
                        humidity = round(sensor.humidity, 2)
                        barometric_pressure = round(sensor.pressure, 2)
                    except Exception as e:
                        logger.error(f"Failed to initialize BME280: {e}")
                        logger.error("Check I2C connections and address (0x76 or 0x77)")
                        raise
                except Exception as e:
                    logger.error(f"Failed to initialize I2C: {e}")
                    logger.error(f"Generating random sensor data for testing")
                    traceback.print_exc()

                    def generate_random_readings(data_type):
                        base_value = DATA_COLLECTION_METRICS[data_type]['base_value']
                        variance = DATA_COLLECTION_METRICS[data_type]['variance']

                        if base_value is not None and variance is not None:
                            anomaly_rate = random.uniform(0.01, 100.00)
                            has_anomaly = anomaly_rate < DATA_COLLECTION_METRICS[data_type]['anomaly_rate']

                            seed = (random.random() - 0.5)
                            value = round(
                                (base_value + (seed * variance) + (2 * variance if has_anomaly else 0)) * 10) / 10
                            return value

                    temperature = generate_random_readings('temperature')
                    humidity = generate_random_readings('humidity')
                    barometric_pressure = generate_random_readings('barometric_pressure')

                logger.info(f"Temperature: {temperature} C")
                logger.info(f"Humidity: {humidity}%")
                logger.info(f"Barometric Pressure: {barometric_pressure} hPa")

                def post_sensor_data(data_type_id, value):
                    try:
                        data = {
                            'dataTypeId': data_type_id,
                            'value': value,
                            'datetime': datetime.now(timezone.utc).isoformat()
                        }
                        logger.info(f"Posting sensor data : {data}")
                        response = requests.post(SENSOR_DATA_API_URL, json=[data])
                        if response.status_code == 200:
                            logger.info("Sensor data posted successfully")
                    except Exception as e:
                        logger.error(f"Error posting sensor data: {e}")

                sensors = list(mongo.sensors_collection.find({"beehive_id": BEEHIVE_ID, "active": True}))
                logger.info(f"sensors: {len(sensors)}")
                for sensor in sensors:
                    logger.info(f"sensor: {sensor}")
                    if 'temperature' in sensor['data_capture']:
                        data_types = mongo.data_types_collection.find({'sensor_id': util.objectid_to_str(sensor['_id']), 'data_type': 'temperature'})
                        for data_type in data_types:
                            post_sensor_data(util.objectid_to_str(data_type['_id']), temperature)
                    if 'humidity' in sensor['data_capture']:
                        data_types = mongo.data_types_collection.find({'sensor_id': util.objectid_to_str(sensor['_id']), 'data_type': 'humidity'})
                        for data_type in data_types:
                            post_sensor_data(util.objectid_to_str(data_type['_id']), humidity)
                    if 'barometric_pressure' in sensor['data_capture']:
                        data_types = mongo.data_types_collection.find({'sensor_id': util.objectid_to_str(sensor['_id']), 'data_type': 'barometric_pressure'})
                        for data_type in data_types:
                            post_sensor_data(util.objectid_to_str(data_type['_id']), barometric_pressure)

            except Exception as e:
                logger.error(f"Error collecting sensor data: {e}")
                traceback.print_exc()

            # Step 3: Capture image and post to API
            try:
                logger.info("")
                logger.info("Step 3: Capturing image...")
                handle_camera_capture({'context': 'data_collection', 'sensorId': BEE_COUNTER_CAMERA_SENSOR_ID})
            except Exception as e:
                logger.error(f"Error capturing image: {e}")
                traceback.print_exc()

            # Return servo to neutral position
            if servo_available:
                try:
                    logger.info("\nStep 4: Returning servo to neutral position...")
                    data_collection_servo.angle = 0 # Return to neutral position
                    time.sleep(1)
                    logger.info("Servo returned to neutral position")
                except Exception as e:
                    logger.error(f"Error returning servo to neutral position: {e}")

            logger.info("Data collection completed successfully!")
            logger.info("=" * 60)

        except Exception as e:
            logger.error(f"Error executing data collection: {e}")
            traceback.print_exc()
            # Continue running despite error
            pass



if __name__ == '__main__':
    import atexit
    import signal

    atexit.register(cleanup)

    def signal_handler(signal, frame):
        logger.info('Shutting down...')
        cleanup()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    logger.info("\n\n\n")
    logger.info("=" * 60)
    logger.info("Starting Apiculture IoT Websocket Control API...")
    logger.info("=" * 60)
    logger.info("\n\n\n")

    # Execute data collection in a fixed interval (start as background thread)
    threading.Thread(target=execute_data_collection, daemon=True).start()

    socketio.run(app, host='0.0.0.0', port=5000, debug=False, allow_unsafe_werkzeug=True)
