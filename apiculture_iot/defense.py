#!/usr/bin/env python3
"""
Defense System for Apiculture IoT

This system continuously monitors the hive by capturing images and analyzing them
through an API. If threats are detected, it can activate water sprinkler defense mechanism.

Features:
  - Captures multiple images every 5 minutes during a servo sweep
  - Posts images to API for threat detection
  - Activates water sprinkler (DC motor valve) if threats detected in any image
  - Alternates servo sweep direction each cycle
  - Runs as background service
"""

import sys
import requests
import time
import os
import logging
from datetime import datetime, timezone
import json
import random
import shutil

from apiculture_iot.data_collection import mongo, util
from apiculture_iot.util.config import API_HOST, API_PORT, DEFENSE_CHECK_INTERVAL, WATER_SPRINKLER_DURATION, \
    DEFENSE_CAMERA_SENSOR_ID

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s:%(lineno)d - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('apiculture-iot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('defense')
logger.setLevel(logging.INFO)


# Configuration
DEFENSE_API_URL = f'http://{API_HOST}:{API_PORT}/api/images'
ALERT_API_URL = f'http://{API_HOST}:{API_PORT}/api/alerts'

# GPIO Configuration
SPRINKLER_PIN = 23
CAMERA_SERVO_PIN = 22

# Servo and capture configuration
SERVO_MIN_ANGLE = 0
SERVO_MAX_ANGLE = 180
NUM_CAPTURE_POINTS = 5  # Number of images to capture during sweep
SWEEP_STEP = (SERVO_MAX_ANGLE - SERVO_MIN_ANGLE) // (NUM_CAPTURE_POINTS - 1) if NUM_CAPTURE_POINTS > 1 else 0

# Storage directories
IMAGE_PATH = "/home/apiculture/photos"
os.makedirs(IMAGE_PATH, exist_ok=True)


try:
    from picamera2 import Picamera2
    camera_available = True
except ImportError:
    camera_available = False
    Picamera2 = None

try:
    import RPi.GPIO as GPIO
    gpio_available = True
except ImportError:
    gpio_available = False
    GPIO = None

# Hardware availability
sprinkler_available = gpio_available
camera_servo_available = gpio_available

# Initialize camera
camera = None
if camera_available:
    try:
        camera = Picamera2()
        logger.info("Camera initialized successfully.")
    except Exception as e:
        logger.error(f"Error initializing camera: {e}")
        camera = None
        camera_available = False

# Global GPIO setup (if available)
if gpio_available:
    try:
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(SPRINKLER_PIN, GPIO.OUT)
        GPIO.setup(CAMERA_SERVO_PIN, GPIO.OUT)
        GPIO.output(SPRINKLER_PIN, GPIO.LOW)
        logger.info("GPIO initialized successfully.")
    except Exception as e:
        logger.error(f"Error initializing GPIO: {e}")
        gpio_available = False

# Defense statistics (for logging)
defense_stat = {
    'total_checks': 0,
    'total_threats': 0,
    'total_sprinkler_activation': 0
}

# Global for alternating direction
sweep_direction_forward = True  # Start with forward sweep (0 to 180)


def activate_sprinkler():
    """Activate water sprinkler for a given duration"""
    if not sprinkler_available:
        logger.warning("Water sprinkler is not available")
        return False

    try:
        logger.info(f"Activating water sprinkler for {WATER_SPRINKLER_DURATION} seconds")
        GPIO.output(SPRINKLER_PIN, GPIO.HIGH)

        # Update statistics
        defense_stat['total_sprinkler_activation'] += 1

        # Wait for duration
        time.sleep(WATER_SPRINKLER_DURATION)

        # Disable sprinkler
        GPIO.output(SPRINKLER_PIN, GPIO.LOW)
        logger.info("Water sprinkler deactivated")
        return True

    except Exception as e:
        logger.error(f"Error activating water sprinkler: {e}")
        try:
            GPIO.output(SPRINKLER_PIN, GPIO.LOW)
        except:
            pass
        return False


def sweep_servo_and_capture(direction_forward):
    """
    Sweep servo in the specified direction and capture multiple images at intervals.
    Returns: (success, threat_detected, captured_files)
    """
    captured_files = []

    # Handle case when camera is not available - use fallback images
    if not camera_available and not camera:
        logger.warning("Camera is not available, using random fallback images from bee_predators folder")

        # Get the project root director (parent of apiculture_iot folder)
        current_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(current_dir)
        bee_predators_dir = os.path.join(project_root, 'images', 'bee_predators')

        if os.path.exists(bee_predators_dir):
            # Get all image files from bee_predators directory
            image_files = [f for f in os.listdir(bee_predators_dir)
                           if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp'))]

            if image_files:
                # Create NUM_CAPTURE_POINTS fallback images
                for i in range(NUM_CAPTURE_POINTS):
                    # Select a random image
                    random_image = random.choice(image_files)
                    random_image_path = os.path.join(bee_predators_dir, random_image)

                    # Create filename with angle simulation
                    simulated_angle = SERVO_MIN_ANGLE + (i * SWEEP_STEP) if direction_forward else SERVO_MAX_ANGLE - (i * SWEEP_STEP)
                    filename = f'defense_sweep_{datetime.now().strftime("%Y%m%d_%H%M%S")}_pos{simulated_angle}.jpg'
                    filepath = os.path.join(IMAGE_PATH, filename)

                    # Copy random image to photo directory
                    shutil.copy(random_image_path, filepath)
                    captured_files.append(filepath)
                    logger.info(f"Random fallback image '{random_image}' copied as: {filepath}")
                    time.sleep(0.1)  # Brief delay between copies

                logger.info(f"Fallback capture completed. Created {len(captured_files)} images from bee_predators.")
                return True, False, captured_files
            else:
                logger.error(f"No images found in bee_predators directory: {bee_predators_dir}")
                return False, False, []
        else:
            logger.error(f"Bee predators directory not found at: {bee_predators_dir}")
            return False, False, []

    # Original camera-based capture logic
    if not camera_servo_available:
        logger.warning("Camera rotation servo is not available")
        return False, False, []

    pwm = None
    try:
        # Set up PWM (50 Hz for servos)
        pwm = GPIO.PWM(CAMERA_SERVO_PIN, 50)
        pwm.start(0)

        def set_servo_angle(ang):
            """Convert angle to duty cycle (0°=2%, 180°=12%)"""
            duty = 2 + (ang / 18.0)
            pwm.ChangeDutyCycle(duty)
            time.sleep(0.1)  # Stabilize

        # Determine sweep angles based on direction
        if direction_forward:
            angles = list(range(SERVO_MIN_ANGLE, SERVO_MAX_ANGLE + 1, round(SWEEP_STEP / 5)))
            angles_to_capture = list(range(SERVO_MIN_ANGLE, SERVO_MAX_ANGLE + 1, SWEEP_STEP))
        else:
            angles = list(range(SERVO_MAX_ANGLE, SERVO_MIN_ANGLE - 1, round(-SWEEP_STEP / 5)))
            angles_to_capture = list(range(SERVO_MAX_ANGLE, SERVO_MIN_ANGLE - 1, -SWEEP_STEP))

        logger.info(f"Starting servo sweep {'forward' if direction_forward else 'backward'} "
                    f"with {len(angles_to_capture)} capture points")

        # Start camera once for efficiency
        camera.start()
        time.sleep(2)  # Initial auto-exposure

        threat_detected = False
        for i, angle in enumerate(angles):
            set_servo_angle(angle)
            if angle not in angles_to_capture:
                continue

            logger.debug(f"Servo at {angle} degrees (point {i+1}/{len(angles)})")

            # Capture image at this position
            filename = f'defense_sweep_{datetime.now().strftime("%Y%m%d_%H%M%S")}_pos{angle}.jpg'
            filepath = os.path.join(IMAGE_PATH, filename)
            camera.capture_file(filepath)
            captured_files.append(filepath)
            logger.info(f"Captured image at {angle}°: {filepath}")

            # Brief pause for motion settle and exposure
            time.sleep(0.5)

        camera.stop()
        logger.info(f"Sweep completed. Captured {len(captured_files)} images.")

        return True, threat_detected, captured_files  # threat_detected updated in analysis

    except Exception as e:
        logger.error(f"Error during servo sweep and capture: {e}")
        if camera:
            try:
                camera.stop()
            except:
                pass
        return False, False, captured_files
    finally:
        if pwm:
            pwm.stop()


def analyze_captured_images(captured_files):
    """
    Upload captured images to API and check for threats.
    Returns: (all_success, any_threat)
    """
    any_threat = False
    all_success = True
    response_with_threat = None

    for filepath in captured_files:
        try:
            filename = os.path.basename(filepath)
            with open(filepath, 'rb') as image_file:
                files = {'image': (filename, image_file, 'image/jpeg')}
                data = {'context': 'defense', 'sensorId': DEFENSE_CAMERA_SENSOR_ID}

                response = requests.post(DEFENSE_API_URL, files=files, data=data, timeout=30)
                response.raise_for_status()

                logger.info(f"Analysis for {filename}: Success")
                response_json = response.json()

                run_sprinkler = response_json.get('run_sprinkler', 'N')
                if run_sprinkler.upper() == 'Y' or run_sprinkler is True:
                    logger.warning(f"Threat detected in {filename}! Preparing sprinkler...")
                    any_threat = True
                    if response_with_threat is None:
                        response_with_threat = response_json
                    elif response_json.get('predator_analysis').get('confidence', 0) > response_with_threat.get('predator_analysis').get('confidence', 0):
                        response_with_threat = response_json
                    defense_stat['total_threats'] += 1
                    # No early break: Analyze all for completeness

        except requests.exceptions.RequestException as e:
            logger.error(f"Error analyzing {filepath}: {e}")
            all_success = False
        except Exception as e:
            logger.error(f"Error processing {filepath}: {e}")
            all_success = False
        finally:
            # Cleanup image after analysis
            if os.path.exists(filepath):
                os.remove(filepath)
                logger.debug(f"Cleaned up image: {filepath}")

    if response_with_threat is not None:
        hive = None
        farm = None

        sensor = mongo.sensors_collection.find_one({"_id": util.str_to_objectid(DEFENSE_CAMERA_SENSOR_ID)})
        if sensor and sensor.get('beehive_id'):
            hive = mongo.hives_collection.find_one({"_id": util.str_to_objectid(sensor['beehive_id'])})
            if hive and hive.get('farm_id'):
                farm = mongo.farms_collection.find_one({"_id": util.str_to_objectid(hive['farm_id'])})

        predator_type = response_with_threat.get('predator_analysis').get('predator') or "unknown predator"
        confidence_pct = int(response_with_threat.get('predator_analysis').get('confidence', 0) * 100)

        event = {
            "alertType": "predator_detected",
            "severity": "critical",
            "title": "Predator Detected!",
            "message": f"A {predator_type} has been detected with {confidence_pct}% confidence. Defense systems activated.",
            "imageId": response_with_threat.get('imageId'),
            "details": {
                "predatorDetectionMethod": response_with_threat.get('predator_analysis').get('details').get("description")
            },
            "timestampMs": datetime.now(timezone.utc).isoformat()
        }

        # Add contextual information if available
        if sensor:
            event["sensorName"] = sensor.get('name', 'Unknown Sensor')
        if hive:
            event["beehiveName"] = hive.get('name', 'Unknown Beehive')
        if farm:
            event["farmName"] = farm.get('name', 'Unknown Farm')

        logger.info(f"Posting alert event : {event}")
        response = requests.post(ALERT_API_URL, json=event)
        if response.status_code == 200:
            logger.info("Alert event posted successfully")

    return all_success, any_threat


def capture_and_analyze_sweep():
    """
    Perform servo sweep, capture multiple images, and analyze them.
    Returns: (success, should_run_sprinkler)
    """
    global sweep_direction_forward

    # Perform sweep and capture
    sweep_success, _, captured_files = sweep_servo_and_capture(sweep_direction_forward)

    if not sweep_success or not captured_files:
        logger.error("Sweep and capture failed.")
        return False, False

    # Analyze all captured images
    analysis_success, any_threat = analyze_captured_images(captured_files)

    # Toggle direction for next loop
    sweep_direction_forward = not sweep_direction_forward
    logger.info(f"Next sweep direction: {'forward' if sweep_direction_forward else 'backward'}")

    return analysis_success, any_threat


def execute_defense_monitoring():
    """Main defense monitoring loop"""
    logger.info("Defense monitoring started...")

    while True:
        try:
            time.sleep(DEFENSE_CHECK_INTERVAL)

            logger.info("=" * 60)
            logger.info(f"Defense check started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            logger.info("=" * 60)

            defense_stat['total_checks'] += 1

            success, should_run_sprinkler = capture_and_analyze_sweep()

            if not success:
                logger.error("Defense monitoring failed. Skipping to next check...")
                continue

            if should_run_sprinkler:
                logger.warning("THREAT DETECTED in at least one image! Activating sprinkler...")
                if activate_sprinkler():
                    logger.info("Sprinkler activated successfully!")
                else:
                    logger.error("Error activating sprinkler.")
            else:
                logger.info("No threats detected in any image.")

            # Log statistics
            logger.info(f"Stats: Checks={defense_stat['total_checks']}, "
                        f"Threats={defense_stat['total_threats']}, "
                        f"Activations={defense_stat['total_sprinkler_activation']}")

            logger.info("Defense check completed.")
            logger.info("=" * 60)

        except Exception as e:
            logger.error(f"Unexpected error in monitoring loop: {e}")
            # Optional: Add retry backoff here


def cleanup():
    """Cleanup on exit"""
    logger.info("Cleaning up...")
    if gpio_available:
        try:
            GPIO.output(SPRINKLER_PIN, GPIO.LOW)
            GPIO.cleanup()
            logger.info("GPIO cleaned up.")
        except Exception as e:
            logger.error(f"GPIO cleanup error: {e}")

    if camera:
        try:
            camera.stop()
            logger.info("Camera stopped.")
        except:
            pass


if __name__ == '__main__':
    import atexit
    import signal

    atexit.register(cleanup)

    def signal_handler(sig, frame):
        logger.info('Shutting down defense system...')
        cleanup()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    logger.info("=" * 60)
    logger.info("Starting Apiculture defense monitoring...")
    logger.info("=" * 60)
    logger.info(f"Check interval: {DEFENSE_CHECK_INTERVAL}s")
    logger.info(f"Sprinkler duration: {WATER_SPRINKLER_DURATION}s")
    logger.info(f"API URL: {DEFENSE_API_URL}")
    logger.info(f"Hardware: Sprinkler={sprinkler_available}, Camera={camera_available}, Servo={camera_servo_available}")
    logger.info(f"Sweep captures: {NUM_CAPTURE_POINTS} images per cycle")
    logger.info(f"Initial sweep direction: {'forward (0-180°)' if sweep_direction_forward else 'backward (180-0°)'}")
    logger.info("\n")

    execute_defense_monitoring()