import board
import busio
try:
    i2c = busio.I2C(board.SCL, board.SDA)
    print("I2C initialized successfully")
    devices = i2c.scan()
    print(f"Detected I2C devices at addresses: {[hex(device) for device in devices]}")
    i2c.deinit()
except Exception as e:
    print(f"I2C error: {e}")