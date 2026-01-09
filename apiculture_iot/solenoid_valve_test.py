import RPi.GPIO as GPIO
import time

# Setup
GPIO.setmode(GPIO.BCM)
SOLENOID_VALVE_PIN = 23
GPIO.setup(SOLENOID_VALVE_PIN, GPIO.OUT)
GPIO.output(SOLENOID_VALVE_PIN, GPIO.LOW)  # Start off

def solenoid_valve_on(duration=5):
    """Turn solenoid valve on for 'duration' seconds."""
    GPIO.output(SOLENOID_VALVE_PIN, GPIO.HIGH)
    time.sleep(duration)
    GPIO.output(SOLENOID_VALVE_PIN, GPIO.LOW)
    print(f"Pump ran for {duration}s")

try:
    # Example: Run for 5 seconds
    solenoid_valve_on(2)
except KeyboardInterrupt:
    GPIO.cleanup()
    print("Cleanup complete.")