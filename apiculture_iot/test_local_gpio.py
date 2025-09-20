import RPi.GPIO as GPIO
import time

GPIO.setmode(GPIO.BCM)
pin = 18  # Example GPIO pin
GPIO.setup(pin, GPIO.OUT)

print(f"Setting GPIO {pin} HIGH")
GPIO.output(pin, GPIO.HIGH)
time.sleep(2)
print(f"Setting GPIO {pin} LOW")
GPIO.output(pin, GPIO.LOW)

GPIO.cleanup()
print("Test complete - no errors means local GPIO works!")