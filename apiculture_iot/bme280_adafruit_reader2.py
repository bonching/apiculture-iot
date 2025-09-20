
import board
import adafruit_bme280
from time import sleep
import busio

# Initialize I2C bus
try:
    i2c = busio.I2C(board.SCL, board.SDA)
except Exception as e:
    print(f"Failed to initialize I2C: {e}")
    exit(1)

# Initialize BME280 sensor
try:
    bme280 = adafruit_bme280.Adafruit_BME280_I2C(i2c, address=0x76)  # Try 0x77 if needed
except ValueError as e:
    print(f"Failed to initialize BME280: {e}")
    print("Check I2C connections and address (0x76 or 0x77)")
    exit(1)

def read_sensor_data():
    try:
        # Read sensor data
        temperature = bme280.temperature
        humidity = bme280.relative_humidity
        pressure = bme280.pressure
        # Print formatted readings
        print(f"Temperature: {temperature:.2f} C")
        print(f"Humidity: {humidity:.2f} %")
        print(f"Pressure: {pressure:.2f} hPa")
    except Exception as e:
        print(f"Error reading sensor data: {e}")

# Main loop
try:
    while True:
        read_sensor_data()
        sleep(2)  # Wait 2 seconds between readings
except KeyboardInterrupt:
    print("Program terminated by user")
finally:
    i2c.deinit()  # Clean up I2C bus