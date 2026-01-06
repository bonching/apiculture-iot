import RPi.GPIO as GPIO
import time

# Setup
GPIO.setmode(GPIO.BCM)
PUMP_PIN = 18  # GPIO 18
GPIO.setup(PUMP_PIN, GPIO.OUT)
GPIO.output(PUMP_PIN, GPIO.LOW)  # Start off

def pump_on(duration=5):
    """Turn pump on for 'duration' seconds."""
    GPIO.output(PUMP_PIN, GPIO.HIGH)
    time.sleep(duration)
    GPIO.output(PUMP_PIN, GPIO.LOW)
    print(f"Pump ran for {duration}s")

try:
    # Example: Run for 5 seconds
    pump_on(5)
except KeyboardInterrupt:
    GPIO.cleanup()
    print("Cleanup complete.")