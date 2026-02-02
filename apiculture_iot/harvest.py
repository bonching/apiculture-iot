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
    - sliding_motor:response - Response to sliding motor control commands
    - extruding_motor:response - Response to extruding motor control commands
    - smoker:response - Response to smoker control commands
    - pump:response - Response to pump control commands
    - error - Error messages
    - connected - Connection established
"""
import subprocess
import sys
import traceback
import logging

from flask import Flask, request
from flask_socketio import SocketIO, emit
from gpiozero import AngularServo, Motor, OutputDevice
import RPi.GPIO as GPIO
import threading
import time
import os
from datetime import datetime

from apiculture_iot.util.config import HARVEST_WEBSOCKET_PORT

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config['SECRET_KEY'] = 'apiculture-iot-secret-key'
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# GPIO Pin Configuration
NEEDLE_SERVO_PIN = 17
POLE_SERVO_PIN = 22
SLIDER_SERVO_PIN = 18
EXTRUDER_SERVO_PIN = 27
SMOKER_PIN = 23
PUMP_PIN = 24

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

slider_servo_state = {
    'angle': 0,
    'mode': 'stopped',
    'last_command': None
}

extruder_servo_state = {
    'angle': 0,
    'mode': 'stopped',
    'last_command': None
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
            'needle_servo': needle_servo_state.copy(),
            'pole_servo': pole_servo_state.copy(),
            'sliding_motor': sliding_motor_state.copy(),
            'extruding_motor': extruding_motor_state.copy(),
            'smoker': smoker_state.copy(),
            'pump': pump_state.copy()
        },
        'device_availability': {
            'needle_servo': 'available',
            'pole_servo': 'available',
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
    logger.info(f"Client disconnected: {client_id} (Total clients: {len(connected_clients)})")


@socketio.on('get:status')
def handle_get_status():
    """Send all device statuses to requesting clients"""
    with state_lock:
        emit('status:all', {
            'success': True,
            'devices': {
                'needle_servo': needle_servo_state.copy(),
                'pole_servo': pole_servo_state.copy(),
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

    logger.info(f"Needle servo:angle - {data}")

    try:
        if not data or 'angle' not in data:
            emit('error', {'message': 'Invalid request - angle parameter is required'})
            return

        angle = float(data['angle'])

        if angle < -180 or angle > 180:
            emit('error', {'message': 'Invalid request - angle must be between -180 and 180 degrees'})
            return

        time.sleep(5)

        # # needle_servo = AngularServo(NEEDLE_SERVO_PIN, min_angle=-90, max_angle=90, initial_angle=None)
        # # needle_servo.angle = 45
        # # print("sleeping for : ", round(angle / 235, 2))
        # # time.sleep(round(angle / 235, 2))
        # # needle_servo.angle = 0
        # # needle_servo.close()
        # # time.sleep(5)
        #
        # # needle_servo = AngularServo(NEEDLE_SERVO_PIN, min_angle=-180, max_angle=180, initial_angle=0)
        # needle_servo.angle = angle
        # # time.sleep(1)
        # # needle_servo.angle = 0
        # # needle_servo.close()
        # # time.sleep(5)
        #
        # def detach_after_move():
        #     time.sleep(0.5)
        #     needle_servo.detach()
        #
        # threading.Thread(target=detach_after_move, daemon=True).start()

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

    logger.info(f"Needle servo:rotate - {data}")

    try:
        if not data or 'direction' not in data:
            emit('error', {'message': 'Missing direction parameter', 'device': 'needle_servo'})
            return

        direction = data['direction'].lower()
        duration = data.get('duration', None)

        if direction not in ['forward', 'reverse', 'stop']:
            emit('error', {'message': 'Direction must be forward, reverse, or stop', 'device': 'needle_servo'})
            return

        time.sleep(5)
        # needle_servo = AngularServo(NEEDLE_SERVO_PIN, min_angle=-180, max_angle=180, initial_angle=0)
        if direction == 'forward':
            # needle_servo.angle = 180
            angle = 180
        elif direction == 'reverse':
            # needle_servo.angle = -180
            angle = -180
        else:
            # needle_servo.angle = 0
            angle = 0

        with state_lock:
            needle_servo_state['angle'] = angle
            needle_servo_state['mode'] = direction
            needle_servo_state['last_command'] = time.strftime("%Y-%m-%d %H:%M:%S")

        # Auto-stop if duration is specified
        if duration and duration > 0 and direction != 'stop':
            # def auto_stop():
            #     time.sleep(float(duration))
            #     # needle_servo.angle = 0
            #     needle_servo.detach()
            #     with state_lock:
            #         needle_servo_state['angle'] = 0
            #         needle_servo_state['mode'] = 'stopped'
            #     broadcast_status_update('needle_servo', needle_servo_state.copy())
            #
            # threading.Thread(target=auto_stop, daemon=True).start()

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


@socketio.on('pole_servo:angle')
def handle_pole_servo_angle(data):
    """Set pole servo to specific angle (for rotating pole)"""

    logger.info(f"Pole servo:angle - {data}")

    try:
        if not data or 'angle' not in data:
            emit('error', {'message': 'Missing angle parameter', 'device': 'pole_servo'})
            return

        angle = float(data['angle'])

        if angle < -180 or angle > 180:
            emit('error', {'message': 'Invalid request - angle must be between -180 and 180 degrees', 'device': 'pole_servo'})
            return

        # Get the client's session id before starting thread
        client_sid = request.sid

        pole_servo = AngularServo(POLE_SERVO_PIN, min_angle=-180, max_angle=180, initial_angle=None)
        pole_servo.angle = angle

        def postprocess_after_move():
            try:
                time.sleep(0.5)
                pole_servo.angle = None
                pole_servo.detach()
                pole_servo.close()

                with state_lock:
                    pole_servo_state['angle'] = angle
                    pole_servo_state['mode'] = 'positioned'
                    pole_servo_state['last_command'] = time.strftime("%Y-%m-%d %H:%M:%S")

                response = {
                    'success': True,
                    'angle': angle,
                    'message': f'Pole servo set to angle {angle} degrees'
                }

                socketio.emit('pole_servo:response', response, room=client_sid, namespace='/')
                broadcast_status_update('pole_servo', pole_servo_state.copy())
            except Exception as e:
                socketio.emit('error', {'message': str(e), 'device': 'pole_servo'}, room=client_sid, namespace='/')

        threading.Thread(target=postprocess_after_move, daemon=True).start()

    except Exception as e:
        emit('error', {'message': f'Error setting pole servo angle: {e}', 'device': 'pole_servo'})


@socketio.on('slider_servo:rotate')
def handle_slider_servo_rotate(data):
    """Control slider servo continuous rotation"""

    logger.info(f"Slider servo:rotate - {data}")

    try:
        if not data or 'direction' not in data:
            emit('error', {'message': 'Missing direction parameter', 'device': 'slider_servo'})
            return

        if not data or 'duration' not in data:
            emit('error', {'message': 'Missing duration parameter', 'device': 'slider_servo'})
            return

        direction = data['direction'].lower()
        duration = data.get('duration', 1)

        if direction not in ['forward', 'backward', 'stop']:
            emit('error', {'message': 'Direction must be forward, backward, or stop', 'device': 'slider_servo'})
            return

        client_sid = request.sid

        slider_servo = AngularServo(SLIDER_SERVO_PIN, min_angle=-180, max_angle=180, initial_angle=None)
        if direction == 'forward':
            slider_servo.angle = 180
            angle = 180
        elif direction == 'backward':
            slider_servo.angle = -180
            angle = -180
        else:
            slider_servo.angle = 0
            angle = 0

        with state_lock:
            slider_servo_state['angle'] = angle
            slider_servo_state['mode'] = direction
            slider_servo_state['last_command'] = time.strftime("%Y-%m-%d %H:%M:%S")

        # Postprocess
        def postprocess_after_rotate():
            try:
                time.sleep(float(duration))
                slider_servo.angle = None
                slider_servo.detach()
                slider_servo.close()
                with state_lock:
                    slider_servo_state['angle'] = 0
                    slider_servo_state['mode'] = 'stopped'
                broadcast_status_update('slider_servo', slider_servo_state.copy())

                response = {
                    'success': True,
                    'direction': direction,
                    'duration': duration,
                    'message': f'Needle servo rotating {direction} for {duration} seconds'
                }

                socketio.emit('slider_servo:response', response, room=client_sid, namespace='/')
                broadcast_status_update('slider_servo', slider_servo_state.copy())
            except Exception as e:
                socketio.emit('error', {'message': str(e), 'device': 'slider_servo'}, room=client_sid, namespace='/')

        threading.Thread(target=postprocess_after_rotate, daemon=True).start()

    except Exception as e:
        emit('error', {'message': str(e), 'device': 'slider_servo'})


@socketio.on('extruder_servo:rotate')
def handle_extruder_servo_rotate(data):
    """Control extruder servo continuous rotation"""

    logger.info(f"Extruder servo:rotate - {data}")

    try:
        if not data or 'direction' not in data:
            emit('error', {'message': 'Missing direction parameter', 'device': 'extruder_servo'})
            return

        if not data or 'duration' not in data:
            emit('error', {'message': 'Missing duration parameter', 'device': 'extruder_servo'})
            return

        direction = data['direction'].lower()
        duration = data.get('duration', 1)

        if direction not in ['extend', 'retract', 'stop']:
            emit('error', {'message': 'Direction must be extend, retract, or stop', 'device': 'extruder_servo'})
            return

        client_sid = request.sid

        extruder_servo = AngularServo(EXTRUDER_SERVO_PIN, min_angle=-180, max_angle=180, initial_angle=None)
        if direction == 'extend':
            extruder_servo.angle = 180
            angle = 180
        elif direction == 'retract':
            extruder_servo.angle = -180
            angle = -180
        else:
            extruder_servo.angle = 0
            angle = 0

        with state_lock:
            extruder_servo_state['angle'] = angle
            extruder_servo_state['mode'] = direction
            extruder_servo_state['last_command'] = time.strftime("%Y-%m-%d %H:%M:%S")

        # Postprocess
        def postprocess_after_rotate():
            try:
                time.sleep(float(duration))
                extruder_servo.angle = None
                extruder_servo.detach()
                extruder_servo.close()
                with state_lock:
                    extruder_servo_state['angle'] = 0
                    extruder_servo_state['mode'] = 'stopped'
                broadcast_status_update('extruder_servo', extruder_servo_state.copy())

                response = {
                    'success': True,
                    'direction': direction,
                    'duration': duration,
                    'message': f'Needle servo rotating {direction} for {duration} seconds'
                }

                socketio.emit('extruder_servo:response', response, room=client_sid, namespace='/')
                broadcast_status_update('extruder_servo', extruder_servo_state.copy())
            except Exception as e:
                socketio.emit('error', {'message': str(e), 'device': 'extruder_servo'}, room=client_sid, namespace='/')

        threading.Thread(target=postprocess_after_rotate, daemon=True).start()

    except Exception as e:
        emit('error', {'message': str(e), 'device': 'extruder_servo'})



# ============= Electric Smoker Websocket Handlers =============

@socketio.on('smoker:control')
def handle_smoker_control(data):
    """Control electric smoker"""

    logger.info(f"Smoker:control - {data}")

    try:
        if not data or 'action' not in data:
            emit('error', {'message': 'Missing action parameter', 'device': 'smoker'})
            return

        if not data or 'duration' not in data:
            emit('error', {'message': 'Missing duration parameter', 'device': 'smoker'})
            return

        action = data['action'].lower()
        duration = data.get('duration', None)

        if action not in ['on', 'off']:
            emit('error', {'message': 'Action must be on or off', 'device': 'smoker'})
            return

        client_sid = request.sid

        GPIO.setmode(GPIO.BCM)
        GPIO.setup(SMOKER_PIN, GPIO.OUT)
        GPIO.output(SMOKER_PIN, GPIO.LOW)

        if action == 'on':
            GPIO.output(SMOKER_PIN, GPIO.HIGH)

            with state_lock:
                smoker_state['active'] = True
                smoker_state['start_time'] = time.time()
                smoker_state['duration'] = duration

            if duration and duration > 0:
                def auto_stop_smoker():
                    try:
                        time.sleep(float(duration))
                        GPIO.output(SMOKER_PIN, GPIO.LOW)
                        with state_lock:
                            smoker_state['active'] = False
                        broadcast_status_update('smoker', smoker_state.copy())

                        response = {
                            'success': True,
                            'action': 'on',
                            'duration': duration,
                            'message': f'Electric smoker turned on for {duration} seconds'
                        }

                        socketio.emit('smoker:response', response, room=client_sid, namespace='/')
                        broadcast_status_update('smoker', extruder_servo_state.copy())
                    except Exception as e:
                        socketio.emit('error', {'message': str(e), 'device': 'smoker'}, room=client_sid, namespace='/')

                threading.Thread(target=auto_stop_smoker, daemon=True).start()

        else: # off
            GPIO.output(SMOKER_PIN, GPIO.LOW)

            with state_lock:
                smoker_state['active'] = False
                smoker_state['duration'] = None

            response = {
                'success': True,
                'action': 'off',
                'message': 'Electric smoker turned off'
            }

            emit('smoker:response', response)
            broadcast_status_update('smoker', smoker_state.copy())

    except Exception as e:
        emit('error', {'message': str(e), 'device': 'smoker'})


# ============= Peristaltic Pump Websocket Handlers =============

@socketio.on('pump:control')
def handle_pump_control(data):
    """Control peristaltic pump"""

    logger.info(f"Pump:control - {data}")

    try:
        if not data or 'action' not in data:
            emit('error', {'message': 'Missing action parameter', 'device': 'pump'})
            return

        if not data or 'duration' not in data:
            emit('error', {'message': 'Missing duration parameter', 'device': 'pump'})
            return

        action = data['action'].lower()
        duration = data.get('duration', None)

        if action not in ['on', 'off']:
            emit('error', {'message': 'Action must be on or off', 'device': 'pump'})
            return

        client_sid = request.sid

        GPIO.setmode(GPIO.BCM)
        GPIO.setup(PUMP_PIN, GPIO.OUT)
        GPIO.output(PUMP_PIN, GPIO.LOW)

        if action == 'on':
            GPIO.output(PUMP_PIN, GPIO.HIGH)

            with state_lock:
                pump_state['active'] = True
                pump_state['start_time'] = time.time()
                pump_state['duration'] = duration

            if duration and duration > 0:
                def auto_stop_pump():
                    try:
                        time.sleep(float(duration))
                        GPIO.output(PUMP_PIN, GPIO.LOW)
                        with state_lock:
                            pump_state['active'] = False
                        broadcast_status_update('pump', pump_state.copy())

                        message = f'Peristaltic pump turned on for {duration} seconds'
                        response = {
                            'success': True,
                            'action': 'on',
                            'duration': duration,
                            'message': message
                        }

                        socketio.emit('pump:response', response, room=client_sid, namespace='/')
                        broadcast_status_update('pump', extruder_servo_state.copy())
                    except Exception as e:
                        socketio.emit('error', {'message': str(e), 'device': 'pump'}, room=client_sid, namespace='/')

                threading.Thread(target=auto_stop_pump, daemon=True).start()

        else:
            GPIO.output(PUMP_PIN, GPIO.LOW)

            with state_lock:
                pump_state['active'] = False
                pump_state['duration'] = None

            response = {
                'success': True,
                'action': 'off',
                'message': 'Peristaltic pump turned off'
            }

        emit('pump:response', response)
        broadcast_status_update('pump', pump_state.copy())

    except Exception as e:
        emit('error', {'message': str(e), 'device': 'pump'})


# ============= Cleanup and Main =============

def cleanup():
    """Cleanup function to stop all devices on exit"""
    # GPIO.setmode(GPIO.BCM)
    # GPIO.output(SMOKER_PIN, GPIO.LOW)
    # GPIO.output(PUMP_PIN, GPIO.LOW)
    GPIO.cleanup()
    logger.info('All devices stopped and cleaned up')



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

    socketio.run(app, host='0.0.0.0', port=HARVEST_WEBSOCKET_PORT, debug=False, allow_unsafe_werkzeug=True)
