import RPi.GPIO as GPIO
import time

# Setup
GPIO.setmode(GPIO.BCM)
SMOKER_PIN = 17  # GPIO 17
GPIO.setup(SMOKER_PIN, GPIO.OUT)
GPIO.output(SMOKER_PIN, GPIO.LOW)  # Start off

def smoker_on(duration=5):
    """Turn smoker on for 'duration' seconds."""
    GPIO.output(SMOKER_PIN, GPIO.HIGH)
    time.sleep(duration)
    GPIO.output(SMOKER_PIN, GPIO.LOW)
    print(f"Pump ran for {duration}s")

try:
    # Example: Run for 5 seconds
    smoker_on(5)
except KeyboardInterrupt:
    GPIO.cleanup()
    print("Cleanup complete.")