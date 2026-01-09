from gpiozero import AngularServo
from time import sleep
import sys

if len(sys.argv) > 1:
    try:
        GPIO_PIN = int(sys.argv[1])
    except ValueError:
        print(f"Invalid GPIO pin: {sys.argv[1]}")
        exit(1)
else:
    GPIO_PIN = 18

if len(sys.argv) > 2:
    try:
        duration = int(sys.argv[2])
    except ValueError:
        print(f"Invalid duration: {sys.argv[2]}")
        exit(1)
else:
    duration = 2

print(f"\n\nSG92R 360 Test on GPIO PIN: {GPIO_PIN}, duration: {duration} seconds")
print(f"Usage: python3 servo.py <GPIO_PIN> (default: 18) <duration> (default: 2 seconds)")
print(f"Example: python3 servo.py 22 5")
print("-" * 60)


servo = AngularServo(GPIO_PIN, min_angle=-90, max_angle=90, initial_angle=None)
try:
    servo.angle = 90
    sleep(duration)
finally:
    servo.angle = 0
    servo.detach()
    servo.close()
print("\nCompleted.")