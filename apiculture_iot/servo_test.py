import RPi.GPIO as GPIO
import time

# Set up GPIO mode (BCM numbering)
GPIO.setmode(GPIO.BCM)

# Servo pin
SERVO_PIN = 22

# Set up PWM on the pin (50 Hz for standard servos)
GPIO.setup(SERVO_PIN, GPIO.OUT)
pwm = GPIO.PWM(SERVO_PIN, 50)  # 50 Hz frequency
pwm.start(0)  # Start PWM with 0% duty cycle


def set_servo_angle(angle):
    """
    Convert angle (0-180) to duty cycle.
    0° = 1ms pulse (2.5% duty), 180° = 2ms pulse (5% duty).
    """
    duty = 2.5 + (angle / 18.0)  # Linear mapping: 0° -> 2.5%, 180° -> 5%
    pwm.ChangeDutyCycle(duty)
    time.sleep(0.1)  # Brief pause for stability


try:
    # Sweep from 0° to 180°
    for angle in range(0, 181, 1):
        set_servo_angle(angle)
        time.sleep(0.015)  # ~15ms delay for smooth motion (adjust for speed)

    # Hold at 180° for 1 second
    time.sleep(1)

    # Sweep back from 180° to 0°
    for angle in range(180, -1, -1):
        set_servo_angle(angle)
        time.sleep(0.015)

    # Hold at 0° for 1 second
    time.sleep(1)

except KeyboardInterrupt:
    print("Stopped by user")

finally:
    # Clean up: Stop PWM and reset GPIO
    pwm.stop()
    GPIO.cleanup()
    print("GPIO cleaned up")