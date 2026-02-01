import board
import busio
import adafruit_bme280

# Create I2C interface (default I2C1 on Pi)
i2c = busio.I2C(board.SCL, board.SDA)

# Initialize sensor (address 0x77 is most common for Adafruit BME280)
bme280 = adafruit_bme280.Adafruit_BME280_I2C(i2c, address=0x77)

# Optional: change sea level pressure for more accurate altitude (hPa)
bme280.sea_level_pressure = 1013.25

print("Temperature: %0.1f °C" % bme280.temperature)
print("Humidity: %0.1f %%" % bme280.relative_humidity)
print("Pressure: %0.1f hPa" % bme280.pressure)
# print("Altitude = %0.2f meters" % bme280.altitude)