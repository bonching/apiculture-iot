import time
from Adafruit_BME280 import *

bme = BME280(t_mode=BME280_OSAMPLE_8, h_mode=BME280_OSAMPLE_8, p_mode=BME280_OSAMPLE_8)
T,H = (None, None)

while True:
    T = bme.read_temperature()
    H = bme.read_humidity()
    
    print(T,H)
    time.sleep(3)