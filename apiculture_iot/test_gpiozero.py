from gpiozero import DigitalOutputDevice
from time import sleep

pin = 17
output = DigitalOutputDevice(pin)

print(f"Setting GPIO {pin} HIGH")
output.on()
sleep(2)
print(f"Setting GPIO {pin} LOW")
output.off()

output.close()
print("Test complete!")