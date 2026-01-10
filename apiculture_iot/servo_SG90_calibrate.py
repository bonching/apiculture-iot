from gpiozero import AngularServo
from time import sleep
import sys
import argparse

# Use argparse for cleaner CLI
parser = argparse.ArgumentParser(description="SG90 Servo Control with Pulse Width Calibration")
parser.add_argument('gpio_pin', nargs='?', type=int, default=18, help="GPIO pin (default: 18)")
parser.add_argument('angle', nargs='?', type=int, default=90, help="Target angle in degrees (default: 90)")
parser.add_argument('--min_pw', type=float, default=0.0005,
                    help="Min pulse width in seconds (default: 0.0005 / 500µs for 0°)")
parser.add_argument('--max_pw', type=float, default=0.0025,
                    help="Max pulse width in seconds (default: 0.0025 / 2500µs for 180°)")
parser.add_argument('--freq', type=float, default=50.0, help="PWM frequency in Hz (default: 50)")
parser.add_argument('--calibrate', action='store_true', help="Sweep mode: Test 0-180° in 10° steps")
parser.add_argument('--min_angle', type=int, default=0, help="Min angle (default: 0)")
parser.add_argument('--max_angle', type=int, default=180, help="Max angle (default: 180)")

args = parser.parse_args()

GPIO_PIN = args.gpio_pin
angle = args.angle
min_pw = args.min_pw
max_pw = args.max_pw
frequency = args.freq
frame_width = 1.0 / frequency
calibrate = args.calibrate
min_angle_val = args.min_angle
max_angle_val = args.max_angle

# Validate angle
if not min_angle_val <= angle <= max_angle_val:
    print(f"Angle {angle} must be between {min_angle_val} and {max_angle_val} degrees.")
    sys.exit(1)

print(f"\n\nSG90 Servo Calibration Test on GPIO PIN: {GPIO_PIN}")
print(f"Pulse Widths: Min={min_pw * 1000:.0f}µs (0°), Max={max_pw * 1000:.0f}µs (180°)")
if calibrate:
    print(f"Sweeping from {min_angle_val}° to {max_angle_val}° in 10° steps (press Ctrl+C to stop)")
else:
    print(f"Moving to {angle}° once, then returning to {min_angle_val}° (PWM freq: {frequency} Hz)")
print(f"Usage: python3 servo.py <GPIO> <ANGLE> [--min_pw <val>] [--max_pw <val>] [--freq <val>] [--calibrate]")
print(f"Calib Example: python3 servo.py 18 --calibrate --min_pw 0.0006 --max_pw 0.0024")
print("-" * 60)

try:
    servo = AngularServo(
        GPIO_PIN,
        min_angle=min_angle_val,
        max_angle=max_angle_val,
        initial_angle=min_angle_val,
        frame_width=frame_width,
        min_pulse_width=min_pw,
        max_pulse_width=max_pw
    )

    if calibrate:
        current_angle = min_angle_val
        step = 10
        while current_angle <= max_angle_val:
            print(f"Moving to {current_angle}°... (Measure rotation)")
            servo.angle = current_angle
            sleep(2)  # Pause to measure
            current_angle += step
        print("Sweep complete—adjust min_pw/max_pw based on measurements.")
    else:
        print(f"Moving to {angle}°...")
        servo.angle = angle
        sleep(1)

        print(f"Returning to {min_angle_val}°...")
        servo.angle = min_angle_val
        sleep(0.5)
        print("\nMovement completed.")

except Exception as e:
    print(f"Error controlling servo: {e}")
finally:
    if 'servo' in locals():
        servo.angle = min_angle_val
        servo.detach()
        servo.close()

print("\nScript completed. Calibrate by tweaking --min_pw/--max_pw and re-running --calibrate.")