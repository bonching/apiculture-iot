import RPi.GPIO as GPIO
import time

# Set up GPIO
GPIO.setmode(GPIO.BCM)
SENSOR_PIN = 24  # GPIO 24 (Pin 18)
GPIO.setup(SENSOR_PIN, GPIO.IN)

try:
    print("Sound Sensor Test (Press Ctrl+C to exit)")
    while True:
        if GPIO.input(SENSOR_PIN):  # D0 is HIGH
            print("Sound Detected!")
        else:
            print("No Sound")
        time.sleep(1.1)
except KeyboardInterrupt:
    print("\nProgram terminated")
finally:
    GPIO.cleanup()