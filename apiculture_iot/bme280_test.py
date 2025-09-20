import board
import adafruit_bme280.basic as adafruit_bme280
import time

i2c = board.I2C()
bme280 = adafruit_bme280.Adafruit_BME280_I2C(i2c)

while True:
    print(f"Temperature: {bme280.temperature:.1f} C")
    print(f"Humidity: {bme280.humidity:.1f} %")
    print(f"Pressure: {bme280.pressure:.1f} hPa")
    time.sleep(2)