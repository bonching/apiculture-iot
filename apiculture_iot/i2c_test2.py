import board
import busio
import time

try:
    i2c = busio.I2C(board.SCL, board.SDA)
    print("I2C bus initialized. Scanning...")
    devices = i2c.scan()
    if devices:
        print("Devices found at addresses:", [hex(device) for device in devices])
    else:
        print("No I2C devices found.")
    i2c.deinit()
except Exception as e:
    print(f"Error initializing I2C: {e}")