from gpiozero import LED
import time

led = LED(17)

while True:
    led.on()
    print("Led on")
    time.sleep(2)
    led.off()
    time.sleep(2)

