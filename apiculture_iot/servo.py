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
servo = AngularServo(GPIO_PIN, min_angle=-90, max_angle=90)  # For 360: Treat as speed; for 180: 0-180

print(f"SG92R 360 Test on GPIO PIN: {GPIO_PIN} - Continuous rotation (Ctrl+C to stop)")
print(f"Usage: python3 servo.py <GPIO_PIN> (default: 18)")
print(f"Example: python3 servo.py 22")
print("-" * 60)

try:
    # Test sequence: Forward 2s, stop 1s, reverse 2s, stop 1s
    while True:
        print("Forward full speed...")
        servo.angle = 90  # +90 = full forward (adjust for your mod)
        sleep(2)
        
        print("Stop...")
        servo.angle = 0   # Neutral = stop
        sleep(1)
        
        print("Reverse full speed...")
        servo.angle = -90 # -90 = full reverse
        sleep(2)
        
        print("Stop...")
        servo.angle = 0
        sleep(1)
except KeyboardInterrupt:
    servo.angle = 0  # Stop on exit
    servo.close()
    print("\nStopped.")