#!/usr/bin/env python3
"""
Websocket API for controlling IOT devices on Raspberry Pi with bi-directional communication

Features:
  - Real-time bi-directional communication via WebSocket
  - Automatic status updates pushed to all connected clients
  - Device control via JSON messages
  - Connection status monitoring

Websocket Events:
  Client -> Server:
    - needle_servo:angle - Set needle servo angle (flip needle to stand/lay down)
    - needle_servo:rotate - Control needle servo rotation
    - pole_servo:angle - Set pole servo angle (rotate pole)
    - pole_servo:rotate - Control pole servo rotation
    - camera:capture - Take a photo
    - camera:video - Start/stop video
    - sliding_motor:control - Control sliding motor (horizontal movement)
    - sliding_motor:stop - Stop sliding motor
    - extruding_motor:control - Control extruding motor (vertical/extrusion)
    - extruding_motor:stop - Stop extruding motor
    - smoker:control - Control smoker
    - pump:control - Control pump
    - get:status - Request all device statuses
    - get:health - Request health check

  Server -> Client:
    - status:update - Automatic status updates when devices change
    - needle_servo:response - Response to needle servo control commands
    - pole_servo:response - Response to pole servo control commands
    - camera:response - Response to camera control commands
    - sliding_motor:response - Response to sliding motor control commands
    - extruding_motor:response - Response to extruding motor control commands
    - smoker:response - Response to smoker control commands
    - pump:response - Response to pump control commands
    - error - Error messages
    - connected - Connection established
"""
import subprocess
import traceback

from flask import Flask, request
from flask_socketio import SocketIO, emit
from gpiozero import AngularServo, Motor, OutputDevice
from picamera2 import Picamera2
import threading
import time
import os
from datetime import datetime

app = Flask(__name__)
app.config['SECRET_KEY'] = 'apiculture-iot-secret-key'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# GPIO Pin Configuration

# Needle Servo (flipping needle to stand/lay down)
NEEDLE_SERVO_PIN = 18

# Pole Servo (rotating pole)
POLE_SERVO_PIN = 12

# Sliding Motor (horizontal movement)
SLIDING_MOTOR_FORWARD_PIN = 23
SLIDING_MOTOR_BACKWARD_PIN = 24
SLIDING_MOTOR_ENABLE_PIN = 25


# Extruding Motor (vertical/extrusion movement)
EXTRUDING_MOTOR_FORWARD_PIN = 5
EXTRUDING_MOTOR_BACKWARD_PIN = 6
EXTRUDING_MOTOR_ENABLE_PIN = 13

SMOKER_PIN = 17
PUMP_PIN = 27

# Initialize Devices
# needle_servo = AngularServo(NEEDLE_SERVO_PIN, min_angle=-180, max_angle=180, initial_angle=None)
# pole_servo = AngularServo(POLE_SERVO_PIN, min_angle=-180, max_angle=180, initial_angle=None)
# sliding_motor = Motor(forward=SLIDING_MOTOR_FORWARD_PIN, backward=SLIDING_MOTOR_BACKWARD_PIN, enable=SLIDING_MOTOR_ENABLE_PIN)
# extruding_motor = Motor(forward=EXTRUDING_MOTOR_FORWARD_PIN, backward=EXTRUDING_MOTOR_BACKWARD_PIN, enable=EXTRUDING_MOTOR_ENABLE_PIN)
# smoker = OutputDevice(SMOKER_PIN)
# pump = OutputDevice(PUMP_PIN)

# Initialize camera
try:
    camera = Picamera2()
    camera_available = True
except Exception as e:
    print(f"Error initializing camera: {e}")
    camera = None
    camera_available = False

# Storage directories
PHOTO_DIR = "/home/apiculture/photos"
VIDEO_DIR = "/home/apiculture/videos"
os.makedirs(PHOTO_DIR, exist_ok=True)
os.makedirs(VIDEO_DIR, exist_ok=True)

# Device states
needle_servo_state = {
    'angle': 0,
    'mode': 'stopped',
    'last_command': None
}

pole_servo_state = {
    'angle': 0,
    'mode': 'stopped',
    'last_command': None
}

camera_state = {
    'recording': False,
    'last_photo': None,
    'last_video': None,
    'video_start_time': None
}

sliding_motor_state = {
    'speed': 0,
    'direction': 'stopped',
    'last_command': None
}

extruding_motor_state = {
    'speed': 0,
    'direction': 'stopped',
    'last_command': None
}

smoker_state = {
    'active': False,
    'start_time': None,
    'duration': None,
    'auto_stop_timer': None
}

pump_state = {
    'active': False,
    'start_time': None,
    'duration': None,
    'auto_stop_timer': None
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
    }, broadcast=True)



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
            'needle_servo': needle_servo_state.copy(),
            'pole_servo': pole_servo_state.copy(),
            'camera': camera_state.copy(),
            'sliding_motor': sliding_motor_state.copy(),
            'extruding_motor': extruding_motor_state.copy(),
            'smoker': smoker_state.copy(),
            'pump': pump_state.copy()
        },
        'device_availability': {
            'needle_servo': 'available',
            'pole_servo': 'available',
            'camera': 'available' if camera_available else 'unavailable',
            'sliding_motor': 'available',
            'extruding_motor': 'available',
            'smoker': 'available',
            'pump': 'available'
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
                'needle_servo': needle_servo_state.copy(),
                'pole_servo': pole_servo_state.copy(),
                'camera': camera_state.copy(),
                'sliding_motor': sliding_motor_state.copy(),
                'extruding_motor': extruding_motor_state.copy(),
                'smoker': smoker_state.copy(),
                'pump': pump_state.copy()
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
            'needle_servo': 'available',
            'pole_servo': 'available',
            'camera': 'available' if camera_available else 'unavailable',
            'sliding_motor': 'available',
            'extruding_motor': 'available',
            'smoker': 'available',
            'pump': 'available'
        }
    })


# ============= Servo Motor Websocket Handlers =============

@socketio.on('needle_servo:angle')
def handle_needle_servo_angle(data):
    """Set needle servo to specified angle (for flipping needle to stand/lay down)"""

    print("Needle servo:angle - ", data)

    try:
        if not data or 'angle' not in data:
            emit('error', {'message': 'Invalid request - angle parameter is required'})
            return

        angle = float(data['angle'])

        if angle < -180 or angle > 180:
            emit('error', {'message': 'Invalid request - angle must be between -180 and 180 degrees'})
            return

        needle_servo = AngularServo(NEEDLE_SERVO_PIN, min_angle=-90, max_angle=90, initial_angle=None)
        needle_servo.angle = 90
        time.sleep(round(angle / 90, 2))
        needle_servo.angle = None
        needle_servo.close()
        time.sleep(5)

        with state_lock:
            needle_servo_state['angle'] = angle
            needle_servo_state['mode'] = 'positioned'
            needle_servo_state['last_command'] = time.strftime("%Y-%m-%d %H:%M:%S")

        response = {
            'success': True,
            'angle': angle,
            'message': f'Needle servo set to angle {angle} degrees'
        }

        emit('needle_servo:response', response)
        broadcast_status_update('needle_servo', needle_servo_state.copy())

    except Exception as e:
        emit('error', {'message': f'Error setting needle servo angle: {e}'})


@socketio.on('needle_servo:rotate')
def handle_needle_servo_rotate(data):
    """Control needle servo continuous rotation"""
    try:
        if not data or 'direction' not in data:
            emit('error', {'message': 'Missing direction parameter', 'device': 'needle_servo'})
            return

        direction = data['direction'].lower()
        duration = data.get('duration', None)

        if direction not in ['forward', 'reverse', 'stop']:
            emit('error', {'message': 'Direction must be forward, reverse, or stop', 'device': 'needle_servo'})
            return

        # if direction == 'forward':
        #     needle_servo.angle = 180
        #     angle = 180
        # elif direction == 'reverse':
        #     needle_servo.angle = -180
        #     angle = -180
        # else:
        #     needle_servo.angle = 0
        #     angle = 0

        with state_lock:
            # needle_servo_state['angle'] = angle
            needle_servo_state['mode'] = direction
            needle_servo_state['last_command'] = time.strftime("%Y-%m-%d %H:%M:%S")

        # Auto-stop if duration is specified
        if duration and duration > 0 and direction != 'stop':
            def auto_stop():
                time.sleep(float(duration))
                # needle_servo.angle = 0
                with state_lock:
                    needle_servo_state['angle'] = 0
                    needle_servo_state['mode'] = 'stopped'
                broadcast_status_update('needle_servo', needle_servo_state.copy())

            threading.Thread(target=auto_stop, daemon=True).start()

            response = {
                'success': True,
                'direction': direction,
                'duration': duration,
                'message': f'Needle servo rotating {direction} for {duration} seconds'
            }
        else:
            response = {
                'success': True,
                'direction': direction,
                'message': f'Needle servo {direction}'
            }

        emit('needle_servo:response', response)
        broadcast_status_update('needle_servo', needle_servo_state.copy())

    except Exception as e:
        emit('error', {'message': str(e), 'device': 'needle_servo'})


# @socketio.on('pole_servo:angle')
# def handle_pole_servo_angle(data):
#     """Set pole servo to specific angle (for rotating pole)"""
#     try:
#         if not data or 'angle' not in data:
#             emit('error', {'message': 'Missing angle parameter', 'device': 'pole_servo'})
#             return
#
#         angle = float(data['angle'])
#
#         if angle < -180 or angle > 180:
#             emit('error', {'message': 'Invalid request - angle must be between -180 and 180 degrees', 'device': 'pole_servo'})
#             return
#
#         pole_servo.angle = angle
#
#         with state_lock:
#             pole_servo_state['angle'] = angle
#             pole_servo_state['mode'] = 'positioned'
#             pole_servo_state['last_command'] = time.strftime("%Y-%m-%d %H:%M:%S")
#
#         response = {
#             'success': True,
#             'angle': angle,
#             'message': f'Pole servo set to angle {angle} degrees'
#         }
#
#         emit('pole_servo:response', response)
#         broadcast_status_update('pole_servo', pole_servo_state.copy())
#
#     except Exception as e:
#         emit('error', {'message': f'Error setting pole servo angle: {e}', 'device': 'pole_servo'})
#
#
# @socketio.on('pole_servo:rotate')
# def handle_pole_servo_rotate(data):
#     """Control pole servo continuous rotation"""
#     try:
#         if not data or 'direction' not in data:
#             emit('error', {'message': 'Missing direction parameter', 'device': 'pole_servo'})
#             return
#
#         direction = data['direction'].lower()
#         duration = data.get('duration', None)
#
#         if direction not in ['forward', 'reverse', 'stop']:
#             emit('error', {'message': 'Direction must be forward, reverse, or stop', 'device': 'pole_servo'})
#             return
#
#         if direction == 'forward':
#             pole_servo.angle = 180
#             angle = 180
#         elif direction == 'reverse':
#             pole_servo.angle = -180
#             angle = -180
#         else:
#             pole_servo.angle = 0
#             angle = 0
#
#         with state_lock:
#             pole_servo_state['angle'] = angle
#             pole_servo_state['mode'] = direction
#             pole_servo_state['last_command'] = time.strftime("%Y-%m-%d %H:%M:%S")
#
#         # Auto-stop if duration is specified
#         if duration and duration > 0 and direction != 'stop':
#             def auto_stop():
#                 time.sleep(float(duration))
#                 pole_servo.angle = 0
#                 with state_lock:
#                     pole_servo_state['angle'] = 0
#                     pole_servo_state['mode'] = 'stopped'
#                 broadcast_status_update('pole_servo', pole_servo_state.copy())
#
#             threading.Thread(target=auto_stop, daemon=True).start()
#
#             response = {
#                 'success': True,
#                 'direction': direction,
#                 'duration': duration,
#                 'message': f'Pole servo rotating {direction} for {duration} seconds'
#             }
#         else:
#             response = {
#                 'success': True,
#                 'direction': direction,
#                 'message': f'Pole servo {direction}'
#             }
#
#         emit('pole_servo:response', response)
#         broadcast_status_update('pole_servo', pole_servo_state.copy())
#
#     except Exception as e:
#         emit('error', {'message': str(e), 'device': 'pole_servo'})


# ============= Camera Websocket Handlers =============

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

        filpath = os.path.join(PHOTO_DIR, filename)

        # Configure and capture
        camera.start()
        time.sleep(2)
        camera.capture_file(filpath)
        camera.stop()

        with state_lock:
            camera_state['last_photo'] = filpath

        response = {
            'success': True,
            'filename': filename,
            'filepath': filpath,
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


# ============= DC Motor Websocket Handlers =============
#
# @socketio.on('sliding_motor:control')
# def handle_sliding_motor_control(data):
#     """Control sliding DC motor (horizontal movement)"""
#     try:
#         if not data or 'direction' not in data:
#             emit('error', {'message': 'Missing direction parameter', 'device': 'sliding_motor'})
#             return
#
#         direction = data['direction'].lower()
#         speed = float(data.get('speed', 1.0))
#         duration = data.get('duration', None)
#
#         if direction not in ['forward', 'reverse', 'stop']:
#             emit('error', {'message': 'Direction must be forward, reverse, or stop', 'device': 'sliding_motor'})
#             return
#
#         if speed < 0 or speed > 1:
#             emit('error', {'message': 'Speed must be between 0 and 1', 'device': 'sliding_motor'})
#             return
#
#         # Control motor
#         if direction == 'forward':
#             sliding_motor.forward(speed)
#         elif direction == 'reverse':
#             sliding_motor.backward(speed)
#         else:
#             sliding_motor.stop()
#             speed = 0
#
#         with state_lock:
#             sliding_motor_state['speed'] = speed
#             sliding_motor_state['direction'] = direction
#             sliding_motor_state['last_command'] = time.strftime("%Y-%m-%d %H:%M:%S")
#
#         # Auto-stop if duration is specified
#         if duration and duration > 0 and direction != 'stop':
#             def auto_stop_sliding_motor():
#                 time.sleep(float(duration))
#                 sliding_motor.stop()
#                 with state_lock:
#                     sliding_motor_state['speed'] = 0
#                     sliding_motor_state['direction'] = 'stopped'
#                 broadcast_status_update('sliding_motor', sliding_motor_state.copy())
#
#             threading.Thread(target=auto_stop_sliding_motor, daemon=True).start()
#             response = {
#                 'success': True,
#                 'direction': direction,
#                 'speed': speed,
#                 'duration': duration,
#                 'message': f'Sliding motor moving {direction} at {speed * 100}% speed for {duration} seconds'
#             }
#         else:
#             response = {
#                 'success': True,
#                 'direction': direction,
#                 'speed': speed,
#                 'message': f'Sliding motor moving {direction} at {speed * 100}% speed'
#             }
#
#         emit('sliding_motor:response', response)
#         broadcast_status_update('sliding_motor', sliding_motor_state.copy())
#
#     except Exception as e:
#         emit('error', {'message': str(e), 'device': 'sliding_motor'})
#
#
# @socketio.on('sliding_motor:stop')
# def handle_sliding_motor_stop(data):
#     """Stop sliding DC motor"""
#     try:
#         sliding_motor.stop()
#
#         with state_lock:
#             sliding_motor_state['speed'] = 0
#             sliding_motor_state['direction'] = 'stopped'
#             sliding_motor_state['last_command'] = time.strftime("%Y-%m-%d %H:%M:%S")
#
#         response = {
#             'success': True,
#             'message': 'Sliding motor stopped'
#         }
#
#         emit('sliding_motor:response', response)
#         broadcast_status_update('sliding_motor', sliding_motor_state.copy())
#
#     except Exception as e:
#         emit('error', {'message': str(e), 'device': 'sliding_motor'})
#
#
# @socketio.on('extruding_motor:control')
# def handle_extruding_motor_control(data):
#     """Control extruding DC motor (vertical/extrusion movement)"""
#     try:
#         if not data or 'direction' not in data:
#             emit('error', {'message': 'Missing direction parameter', 'device': 'extruding_motor'})
#             return
#
#         direction = data['direction'].lower()
#         speed = float(data.get('speed', 1.0))
#         duration = data.get('duration', None)
#
#         if direction not in ['up', 'down', 'stop']:
#             emit('error', {'message': 'Direction must be up, down, or stop', 'device': 'extruding_motor'})
#             return
#
#         if speed < 0 or speed > 1:
#             emit('error', {'message': 'Speed must be between 0 and 1', 'device': 'extruding_motor'})
#             return
#
#         # Control motor
#         if direction == 'up':
#             extruding_motor.forward(speed)
#         elif direction == 'down':
#             extruding_motor.backward(speed)
#         else:
#             extruding_motor.stop()
#             speed = 0
#
#         with state_lock:
#             extruding_motor_state['speed'] = speed
#             extruding_motor_state['direction'] = direction
#             extruding_motor_state['last_command'] = time.strftime("%Y-%m-%d %H:%M:%S")
#
#         # Auto-stop if duration is specified
#         if duration and duration > 0 and direction != 'stop':
#             def auto_stop_extruding_motor():
#                 time.sleep(float(duration))
#                 extruding_motor.stop()
#                 with state_lock:
#                     extruding_motor_state['speed'] = 0
#                     extruding_motor_state['direction'] = 'stopped'
#                 broadcast_status_update('extruding_motor', extruding_motor_state.copy())
#
#             threading.Thread(target=auto_stop_extruding_motor, daemon=True).start()
#             response = {
#                 'success': True,
#                 'direction': direction,
#                 'speed': speed,
#                 'duration': duration,
#                 'message': f'Extruding motor moving {direction} at {speed * 100}% speed for {duration} seconds'
#             }
#         else:
#             response = {
#                 'success': True,
#                 'direction': direction,
#                 'speed': speed,
#                 'message': f'Extruding motor moving {direction} at {speed * 100}% speed'
#             }
#
#         emit('extruding_motor:response', response)
#         broadcast_status_update('extruding_motor', extruding_motor_state.copy())
#
#     except Exception as e:
#         emit('error', {'message': str(e), 'device': 'extruding_motor'})
#
#
# @socketio.on('extruding_motor:stop')
# def handle_extruding_motor_stop(data):
#     """Stop extruding DC motor"""
#     try:
#         extruding_motor.stop()
#
#         with state_lock:
#             extruding_motor_state['speed'] = 0
#             extruding_motor_state['direction'] = 'stopped'
#             extruding_motor_state['last_command'] = time.strftime("%Y-%m-%d %H:%M:%S")
#
#         response = {
#             'success': True,
#             'message': 'Extruding motor stopped'
#         }
#
#         emit('extruding_motor:response', response)
#         broadcast_status_update('extruding_motor', extruding_motor_state.copy())
#
#     except Exception as e:
#         emit('error', {'message': str(e), 'device': 'extruding_motor'})


# ============= Electric Smoker Websocket Handlers =============
#
# @socketio.on('smoker:control')
# def handle_smoker_control(data):
#     """Control electric smoker"""
#     try:
#         if not data or 'action' not in data:
#             emit('error', {'message': 'Missing action parameter', 'device': 'smoker'})
#             return
#
#         action = data['action'].lower()
#         duration = data.get('duration', None)
#
#         if action not in ['on', 'off']:
#             emit('error', {'message': 'Action must be on or off', 'device': 'smoker'})
#             return
#
#         if action == 'on':
#             smoker.on()
#
#             with state_lock:
#                 smoker_state['active'] = True
#                 smoker_state['start_time'] = time.time()
#                 smoker_state['duration'] = duration
#
#             # Auto-stop if duration is specified
#             if duration and duration > 0:
#                 def auto_stop_smoker():
#                     time.sleep(float(duration))
#                     smoker.off()
#                     with state_lock:
#                         smoker_state['active'] = False
#                     broadcast_status_update('smoker', smoker_state.copy())
#
#                 threading.Thread(target=auto_stop_smoker, daemon=True).start()
#                 response = {
#                     'success': True,
#                     'action': 'on',
#                     'duration': duration,
#                     'message': f'Electric smoker turned on for {duration} seconds'
#                 }
#             else:
#                 response = {
#                     'success': True,
#                     'action': 'on',
#                     'message': 'Electric smoker turned on'
#                 }
#
#         else: # off
#             smoker.off()
#
#             with state_lock:
#                 smoker_state['active'] = False
#                 smoker_state['duration'] = None
#
#             response = {
#                 'success': True,
#                 'action': 'off',
#                 'message': 'Electric smoker turned off'
#             }
#
#         emit('smoker:response', response)
#         broadcast_status_update('smoker', smoker_state.copy())
#
#     except Exception as e:
#         emit('error', {'message': str(e), 'device': 'smoker'})


# ============= Peristaltic Pump Websocket Handlers =============
#
# @socketio.on('pump:control')
# def handle_pump_control(data):
#     """Control peristaltic pump"""
#     try:
#         if not data or 'action' not in data:
#             emit('error', {'message': 'Missing action parameter', 'device': 'pump'})
#             return
#
#         action = data['action'].lower()
#         duration = data.get('duration', None)
#         volume_ml = data.get('volume_ml', None)
#
#         if action not in ['on', 'off']:
#             emit('error', {'message': 'Action must be on or off', 'device': 'pump'})
#             return
#
#         # If volume is specified, calculate duration (assuming 1ml/sec - calibrate for your pump)
#         ML_PER_SEC = 1.0
#         if volume_ml and not duration:
#             duration = volume_ml / ML_PER_SEC
#
#         if action == 'on':
#             pump.on()
#
#             with state_lock:
#                 pump_state['active'] = True
#                 pump_state['start_time'] = time.time()
#                 pump_state['duration'] = duration
#
#             # Auto-stop if duration is specified
#             if duration and duration > 0:
#                 def auto_stop_pump():
#                     time.sleep(float(duration))
#                     pump.off()
#                     with state_lock:
#                         pump_state['active'] = False
#                     broadcast_status_update('pump', pump_state.copy())
#
#                 threading.Thread(target=auto_stop_pump, daemon=True).start()
#
#                 message = f'Peristaltic pump turned on for {duration} seconds'
#                 if volume_ml:
#                     message += f' (approx {volume_ml}ml)'
#
#                 response = {
#                     'success': True,
#                     'action': 'on',
#                     'duration': duration,
#                     'volume_ml': volume_ml,
#                     'message': message
#                 }
#             else:
#                 response = {
#                     'success': True,
#                     'action': 'on',
#                     'message': 'Peristaltic pump turned on'
#                 }
#
#         else: # off
#             pump.off()
#
#             with state_lock:
#                 pump_state['active'] = False
#                 pump_state['duration'] = None
#
#             response = {
#                 'success': True,
#                 'action': 'off',
#                 'message': 'Peristaltic pump turned off'
#             }
#
#         emit('pump:response', response)
#         broadcast_status_update('pump', pump_state.copy())
#
#     except Exception as e:
#         emit('error', {'message': str(e), 'device': 'pump'})


# ============= Cleanup and Main =============

def cleanup():
    """Cleanup function to stop all devices on exit"""
    # needle_servo.angle = 0
    # needle_servo.close()
    # pole_servo.angle = 0
    # sliding_motor.stop()
    # extruding_motor.stop()
    # smoker.off()
    # pump.off()
    if camera_available and camera_state['recording']:
        try:
            camera.stop_recording()
        except:
            pass
    print('All devices stopped and cleaned up')



if __name__ == '__main__':
    import atexit
    atexit.register(cleanup)

    print("\n\n\n")
    print("=" * 60)
    print("Starting Apiculture IoT Websocket Control API...")
    print("=" * 60)
    print("\n\n\n")

    socketio.run(app, host='0.0.0.0', port=5000, debug=True, allow_unsafe_werkzeug=True)
