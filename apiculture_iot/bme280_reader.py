import smbus2
import bme280
import time

# Initialize I2C bus (I2C1 is used on Raspberry Pi 5)
port = 1
address = 0x76  # Default I2C address for GY-BME280 (use 0x77 if needed)
bus = smbus2.SMBus(port)

# Load calibration parameters
calibration_params = bme280.load_calibration_params(bus, address)

# Continuously read sensor data
try:
    while True:
        # Take a sample from the sensor
        data = bme280.sample(bus, address, calibration_params)
        
        # Extract data
        temperature = data.temperature
        humidity = data.humidity
        pressure = data.pressure
        
        # Print readings
        print(f"Temperature: {temperature:.1f} C")
        print(f"Humidity: {humidity:.1f} %")
        print(f"Pressure: {pressure:.1f} hPa")
        print("-" * 30)
        
        # Wait for 5 seconds before next reading
        time.sleep(5)

except KeyboardInterrupt:
    print("Program stopped by user")
except Exception as e:
    print(f"An error occurred: {e}")
finally:
    bus.close()