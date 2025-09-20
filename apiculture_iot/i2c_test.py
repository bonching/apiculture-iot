import smbus2
import time

bus = smbus2.SMBus(1)
address = 0x77  # Try 0x76 or 0x77

try:
    bus.read_byte(address)
    print(f"Device detected at address 0x{address:02x}")
except OSError as e:
    print(f"No device at address 0x{address:02x}: {e}")