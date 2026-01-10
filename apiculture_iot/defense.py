#! /usr/bin/env python3
"""
Defense System for Apiculture IoT

This system continuously monitors the hive by capturing images and analyzing them
through an API. If threats are detected, it can activate water sprinkler defense mechanism.

Features:
  - Captures images every 5 minutes
  - Posts images to API for threat detection
  - Activates water sprinkler (DC motor valve) if threats detected
  - Runs as background service
"""

import sys
import requests
import time
import os
from datetime import datetime
from picamera2 import Picamera2
import RPi.GPIO as GPIO

from apiculture_iot.util.config import API_HOST, API_PORT

# Configuration
DEFENSE_CHECK_INTERVAL = 30 * 1
DEFENSE_API_URL = f'http://{API_HOST}:{API_PORT}/api/images'
WATER_SPRINKLER_DURATION = 2

# GPIO Configuration
SPRINKLER_PIN = 23
CAMERA_SERVO_PIN = 22

# Storage directories
IMAGE_PATH = "/home/apiculture/photos"

os.makedirs(IMAGE_PATH, exist_ok=True)

# Initialize sprinkler
sprinkler_available = True

# Initialize camera
try:
    camera = Picamera2()
    camera_available = True
    print("Camera initialized successfully.")
except Exception as e:
    print(f"Error initializing camera: {e}")
    camera = None
    camera_available = False

# Initialize camera rotation servo
try:
    # camera_servo = AngularServo(CAMERA_SERVO_PIN, min_angle=-90, max_angle=90)
    camera_servo_available = True
    print(f"Camera rotation servo initialized on GPIO PIN: {CAMERA_SERVO_PIN}")
except Exception as e:
    print(f"Error initializing camera rotation servo: {e}")
    camera_servo = None
    camera_servo_available = False

# Defense statistics (for logging)
defense_stat = {
    'total_checks': 0,
    'total_threats': 0,
    'total_sprinkler_activation': 0
}


def activate_sprinkler():
    """Activate water sprinkler for a given duration"""
    if not sprinkler_available:
        print("Water sprinkler is not available")
        return False

    try:
        print(f"Activating water sprinkler for {WATER_SPRINKLER_DURATION} seconds")

        GPIO.setmode(GPIO.BCM)
        GPIO.setup(SPRINKLER_PIN, GPIO.OUT)
        GPIO.output(SPRINKLER_PIN, GPIO.HIGH)

        # Update statistics
        defense_stat['total_sprinkler_activation'] += 1

        # Wait for duration
        time.sleep(WATER_SPRINKLER_DURATION)

        # Disable sprinkler
        GPIO.output(SPRINKLER_PIN, GPIO.LOW)

        print("Water sprinkler deactivated")

        return True

    except Exception as e:
        print(f"Error activating water sprinkler: {e}")
        try:
            GPIO.output(SPRINKLER_PIN, GPIO.LOW)
        except:
            pass
        return False


def rotate_camera(angle):
    """Rotate camera to a given angle"""
    if not camera_servo_available:
        print("Camera rotation servo is not available")
        return False

    try:
        GPIO.setmode(GPIO.BCM)

        # Set up PWM on the pin (50 Hz for standard servos)
        GPIO.setup(CAMERA_SERVO_PIN, GPIO.OUT)
        pwm = GPIO.PWM(CAMERA_SERVO_PIN, 50)  # 50 Hz frequency
        pwm.start(0)  # Start PWM with 0% duty cycle

        def set_servo_angle(angle):
            """
            Convert angle (0-180) to duty cycle.
            Adjusted mapping for Pi compatibility: 0° ≈ 2%, 180° ≈ 12% (covers 0.5-2.5ms pulse).
            """
            duty = 2 + (angle / 18.0)  # Linear mapping with offset for jitter reduction
            pwm.ChangeDutyCycle(duty)
            time.sleep(0.1)  # Brief pause for stability

        try:
            # Sweep from 0° to 180°
            for angle in range(0, 181, 1):
                set_servo_angle(angle)
                time.sleep(0.015)  # ~15ms delay for smooth motion (adjust for speed)

            # Hold at 180° for 1 second
            time.sleep(1)

            # Sweep back from 180° to 0°
            # for angle in range(180, -1, -1):
            #     set_servo_angle(angle)
            #     time.sleep(0.015)

            # Hold at 0° for 1 second
            # time.sleep(1)

        except KeyboardInterrupt:
            print("Stopped by user")

        finally:
            # Stop PWM (cleanup omitted to avoid the bug)
            pwm.stop()
            print("PWM stopped - GPIO resources auto-released on exit")

        return True
    except Exception as e:
        print(f"Error rotating camera: {e}")
        return False


def capture_and_analyze_image():
    """
    Capture image and post to API for threat detection
    Returns: (success, run_sprinkler)
    """
    if not camera_available:
        print("Camera is not available")
        return False, False

    try:
        # Rotate camera to scanning position (0 degrees to center)
        rotate_camera(45)

        # Generate filename with timestamp
        filename = f'defense_{datetime.now().strftime("%Y%m%d_%H%M%S")}.jpg'
        filepath = os.path.join(IMAGE_PATH, filename)

        print(f"Capturing image to {filepath}")

        # Start camera and capture image
        camera.start()
        time.sleep(2)
        camera.capture_file(filepath)
        camera.stop()

        print(f"Image captured successfully: {filepath}")

        # Upload the image to API for threat detection
        with open(filepath, 'rb') as image_file:
            files = {'image': (filename, image_file, 'image/jpeg')}
            data = {'context': 'defense'}

            try:
                print(f"Posting image to API for threat detection: {DEFENSE_API_URL}")
                response = requests.post(DEFENSE_API_URL, files=files, data=data, timeout=30)

                if response.status_code == 201:
                    print("Threat detection completed successfully!")
                    print(f"Response: {response.text}")

                    try:
                        # Parse JSON response
                        response_json = response.json()

                        # Check if we should run sprinkler
                        run_sprinkler = response_json.get('run_sprinkler', 'N')

                        if run_sprinkler.upper() == 'Y' or run_sprinkler is True:
                            print("Threat detected! Activating sprinkler...")
                            defense_stat['total_threats'] += 1
                            return True, True
                        else:
                            print("No threat detected.")
                            return True, False

                    except Exception as e:
                        print(f"Error parsing JSON response: {e}")
                        return True, False
                else:
                    print(f"Error posting image to API: {response.text}")
                    print(f"Response: {response.text}")
                    return False, False

            except requests.exceptions.RequestException as e:
                print(f"Error posting image to API: {e}")
                return False, False

    except Exception as e:
        print(f"Error capturing image: {e}")
        return False, False


# ============ Defense monitoring loop ============
def execute_defense_monitoring():
    """
    Main defense monitoring loop:
    1. Capture image
    2. Post to API for threat detection
    3. Wait for response
    4. If run_sprinkler=Y, activate sprinkler for WATER_SPRINKLER_DURATION seconds
    5. Repeat every DEFENSE_CHECK_INTERVAL seconds
    """
    print("Defense monitoring started...")

    while True:
        try:
            time.sleep(DEFENSE_CHECK_INTERVAL)

            print("\n" + "=" * 60)
            print(f"Defense check interval reached, starting defense monitoring...")
            print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            print("=" * 60)

            # update statistics
            defense_stat['total_checks'] += 1

            # Step 1, 2, & 3: Capture image and post to API for threat detection
            success, should_run_sprinkler = capture_and_analyze_image()

            if not success:
                print("Defense monitoring failed. Skipping to next check...")
                continue

            # Step 4: activate sprinkler if threat detected
            if should_run_sprinkler:
                print("\nTHREAT DETECTED! Activating sprinkler...")
                activate_success = activate_sprinkler()

                if activate_success:
                    print("Sprinkler activated successfully!")
                else:
                    print("Error activating sprinkler. Skipping to next check...")
            else:
                print("\nNo threat detected. Skipping to next check...")

            # Log statistics
            print(f"\nStatistics: Checks={defense_stat['total_checks']}, "
                  f"Threats={defense_stat['total_threats']}, "
                  f"Sprinkler Activations={defense_stat['total_sprinkler_activation']}")

            print("\n Defense check completed successfully!")
            print("=" * 60 + "\n")

        except Exception as e:
            print(f"Error in defense monitoring: {e}")
            # Continue running despite error
            pass


def cleanup():
    """Cleanup function to stop all devices on exit"""
    print("Cleaning up defense monitoring resources...")

    if sprinkler_available:
        try:
            GPIO.output(SPRINKLER_PIN, GPIO.LOW)
            GPIO.cleanup()
            print("Water sprinkler deactivated successfully.")
        except:
            pass

    # if camera_servo_available:
    #     try:
    #         camera_servo.angle = 0
    #         time.sleep(0.5)
    #         camera_servo.close()
    #         print("Camera servo turned to neutral and closed.")
    #     except:
    #         pass

    if camera_available:
        try:
            camera.stop()
            print("Camera stopped")
        except:
            pass

    print("All devices stopped and cleaned up")


if __name__ == '__main__':
    import atexit
    import signal

    atexit.register(cleanup)

    def signal_handler(signal, frame):
        print('Shutting down defense system...')
        cleanup()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    print("\n\n")
    print("=" * 60)
    print("Starting Apiculture defense monitoring...")
    print("=" * 60)
    print(f"Check interval: {DEFENSE_CHECK_INTERVAL} seconds")
    print(f"Sprinkler duration: {WATER_SPRINKLER_DURATION} seconds")
    print(f"API URL: {DEFENSE_API_URL}")
    print(f"Sprinkler available: {sprinkler_available}")
    print(f"Camera available: {camera_available}")
    print(f"Camera rotation servo available: {camera_servo_available}")
    print("\n")

    # Start defense monitoring loop
    execute_defense_monitoring()
