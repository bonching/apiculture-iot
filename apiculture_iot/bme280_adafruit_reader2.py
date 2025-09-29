
import board
#import adafruit_bme280
import adafruit_bme280.basic as adafruit_bme280
from time import sleep
import busio

def read_sensor_data():
    # Initialize I2C bus
    try:
        #i2c = busio.I2C(board.SCL, board.SDA)
        i2c = board.I2C()
    except Exception as e:
        print(f"Failed to initialize I2C: {e}")
        #exit(1)
        
    # Initialize BME280 sensor
    try:
        #bme280 = adafruit_bme280.Adafruit_BME280_I2C(i2c, address=0x76)  # Try 0x77 if needed
        sensor = adafruit_bme280.Adafruit_BME280_I2C(i2c, address=0x76)
    except Exception as e:
        print(f"Failed to initialize BME280: {e}")
        print("Check I2C connections and address (0x76 or 0x77)")
        return
        #exit(1)

    try:
        # Read sensor data
        temperature = sensor.temperature
        humidity = sensor.relative_humidity
        pressure = sensor.pressure
        # Print formatted readings
        print(f"Temperature: {temperature:.2f} C")
        print(f"Humidity: {humidity:.2f} %")
        print(f"Pressure: {pressure:.2f} hPa")
    except Exception as e:
        print(f"Error reading sensor data: {e}")

# Main loop
try:
    loop_count = 1
    while True:
        read_sensor_data()
        print("Loop count: " + str(loop_count))
        loop_count = loop_count + 1
        sleep(2)  # Wait 2 seconds between readings
except KeyboardInterrupt:
    print("Program terminated by user")
#finally:
    #i2c.deinit()  # Clean up I2C bus
