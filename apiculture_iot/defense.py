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
from gpiozero import OutputDevice, AngularServo

# Configuration
DEFENSE_CHECK_INTERVAL = 60 * 5
DEFENSE_API_URL = 'http://192.168.68.106:8081/api/images'
WATER_SPRINKLER_DURATION = 10

# GPIO Configuration
SPRINKLER_PIN = 23
CAMERA_SERVO_PIN = 18

# Storage directories
IMAGE_PATH = "/home/apiculture/photos"

os.makedirs(IMAGE_PATH, exist_ok=True)

# Initialize camera
try:
    camera = Picamera2()
    camera_available = True
    print("Camera initialized successfully.")
except Exception as e:
    print(f"Error initializing camera: {e}")
    camera = None
    camera_available = False

# Initialize water sprinkler (simple on/off control)
try:
    sprinkler = OutputDevice(27)
    sprinkler_available = True
    print(f"Water sprinkler initialized on GPIO PIN: {SPRINKLER_PIN}")
except Exception as e:
    print(f"Error initializing water sprinkler: {e}")
    sprinkler = None
    sprinkler_available = False

# Initialize camera rotation servo
try:
    camera_servo = AngularServo(CAMERA_SERVO_PIN, min_angle=-90, max_angle=90)
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

        # Enable sprinkler
        sprinkler.on()

        # Update statistics
        defense_stat['total_sprinkler_activation'] += 1

        # Wait for duration
        time.sleep(WATER_SPRINKLER_DURATION)

        # Disable sprinkler
        sprinkler.off()

        print("Water sprinkler deactivated")

        return True

    except Exception as e:
        print(f"Error activating water sprinkler: {e}")
        try:
            sprinkler.off()
        except:
            pass
        return False


def rotate_camera(angle):
    """Rotate camera to a given angle"""
    if not camera_servo_available:
        print("Camera rotation servo is not available")
        return False

    try:
        print(f"Rotating camera to {angle} degrees")
        camera_servo.angle = angle
        time.sleep(1)
        print("Camera rotated successfully")
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
        rotate_camera(0)

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
                response = requests.post(DEFENSE_API_URL, files=files, data=data, timeout=60)

                if response.status_code == 200:
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
            sprinkler.off()
            print("Water sprinkler deactivated successfully.")
        except:
            pass

    if camera_servo_available:
        try:
            camera_servo.angle = 0
            time.sleep(0.5)
            camera_servo.close()
            print("Camera servo turned to neutral and closed.")
        except:
            pass

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
