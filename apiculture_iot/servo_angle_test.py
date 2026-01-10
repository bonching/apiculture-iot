from gpiozero import AngularServo
from time import sleep
import sys

if len(sys.argv) > 1:
    try:
        GPIO_PIN = int(sys.argv[1])
    except ValueError:
        print(f"Invalid GPIO pin: {sys.argv[1]}")
        sys.exit(1)
else:
    GPIO_PIN = 18

if len(sys.argv) > 2:
    try:
        angle = int(sys.argv[2])
        if not -90 <= angle <= 90:
            print(f"Angle must be between -90 and 90 degrees.")
            sys.exit(1)
    except ValueError:
        print(f"Invalid angle: {sys.argv[2]}")
        sys.exit(1)
else:
    angle = 90

if len(sys.argv) > 3:
    try:
        frequency = float(sys.argv[3])
        if not 20 <= frequency <= 100:
            print(f"Frequency must be between 20 and 100 Hz (typical for servos: 50 Hz).")
            sys.exit(1)
    except ValueError:
        print(f"Invalid frequency: {sys.argv[3]}")
        sys.exit(1)
else:
    frequency = 50.0

frame_width = 1.0 / frequency

print(f"\n\nSG90 Servo Single Movement Test on GPIO PIN: {GPIO_PIN}")
print(f"Moving to {angle}° once, then returning to 0° (PWM frequency: {frequency} Hz)")
print(f"Usage: python3 servo.py <GPIO_PIN> (default: 18) <ANGLE> (default: 90) <FREQUENCY> (default: 50)")
print(f"Example: python3 servo.py 22 45 50")
print("-" * 60)

try:
    servo = AngularServo(
        GPIO_PIN,
        min_angle=-90,
        max_angle=90,
        initial_angle=0,
        frame_width=frame_width
    )
    print(f"Moving to {angle}°...")
    servo.angle = angle
    sleep(1)  # Pause to observe movement

    print("Returning to 0°...")
    servo.angle = 0
    sleep(0.5)
    print("\nMovement completed successfully.")
except Exception as e:
    print(f"Error controlling servo: {e}")
finally:
    if 'servo' in locals():
        servo.angle = 0  # Ensure return to center
        servo.detach()
        servo.close()

print("\nScript completed.")