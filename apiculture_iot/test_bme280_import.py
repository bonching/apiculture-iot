
import board
import lgpio
import adafruit_bme280
print("Modules imported successfully")
print(f"SCL: {board.SCL}, SDA: {board.SDA}")
print(f"Adafruit_BME280_I2C available: {hasattr(adafruit_bme280, 'Adafruit_BME280_I2C')}")
