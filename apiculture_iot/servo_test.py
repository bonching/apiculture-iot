from gpiozero import AngularServo
from time import sleep

# Servo on GPIO 18 (BCM numbering), min/max pulse widths for 0°-180°
servo = AngularServo(22, min_pulse_width=0.001, max_pulse_width=0.002)  # 1ms to 2ms

try:
    # Sweep from 0° to 180°
    for angle in range(0, 181, 1):
        servo.angle = angle
        sleep(0.015)  # ~15ms for smooth motion

    # Hold at 180°
    sleep(1)

    # Sweep back
    for angle in range(180, -1, -1):
        servo.angle = angle
        sleep(0.015)

    # Hold at 0°
    sleep(1)

except KeyboardInterrupt:
    print("Stopped by user")

finally:
    servo.close()  # Safe cleanup built-in
    print("Servo closed")