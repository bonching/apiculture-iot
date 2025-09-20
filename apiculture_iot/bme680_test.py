import adafruit_bme680
import board
import busio
import time

# Initialize I2C bus
i2c = busio.I2C(board.SCL, board.SDA)

# Initialize BME680 sensor (default address 0x76; use 0x77 if ADDR pin is high)
sensor = adafruit_bme680.Adafruit_BME680_I2C(i2c, address=0x76)

# Optional: Set sea-level pressure for accurate altitude (adjust to local value)
sensor.sea_level_pressure = 1013.25

# Main loop to read and print sensor data
while True:
    temperature = sensor.temperature
    humidity = sensor.humidity
    pressure = sensor.pressure
    gas = sensor.gas  # Gas resistance in ohms
    output = f"Temp: {temperature:.2f} C, Hum: {humidity:.2f}%, Pres: {pressure:.2f}hPa, Gas: {gas:.0f}?"
    print(output)
    time.sleep(1)