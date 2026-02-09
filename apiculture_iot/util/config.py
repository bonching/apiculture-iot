import os

API_HOST = os.environ.get('API_HOST', '192.168.68.104')
API_PORT = 8081
MONGODB_URL = f'mongodb://{API_HOST}:27017/?directConnection=true&serverSelectionTimeoutMS=2000&appName=apiculture'

DATA_COLLECTION_WEBSOCKET_PORT = os.environ.get('DATA_COLLECTION_WEBSOCKET_PORT', 5001)
DATA_COLLECTION_INTERVAL = int(os.environ.get('DATA_COLLECTION_INTERVAL', 60*1))
DATA_COLLECTION_SERVO_PIN = os.environ.get('DATA_COLLECTION_SERVO_PIN', 12)
DATA_COLLECTION_BME280_I2C_ADDRESS = 0x77 if os.environ.get('DATA_COLLECTION_BME280_I2C_ADDRESS', '0x76') == '0x77' else 0x76 # Default I2C address for BME280 (use 0x77 if needed)

BEEHIVE_ID = '693ad7c84739d5289a1e0835'
BEE_COUNTER_CAMERA_SENSOR_ID = '693b4c90943e75b9d619e11b'
DEFENSE_CAMERA_SENSOR_ID = '693b4c90943e75b9d619e11c'

DEFENSE_CHECK_INTERVAL = 60
WATER_SPRINKLER_DURATION = 2
DEFENSE_SPRINKLER_PIN = os.environ.get('DEFENSE_SPRINKLER_PIN', 23)
DEFENSE_CAMERA_SERVO_PIN = os.environ.get('DEFENSE_CAMERA_SERVO_PIN', 22)

HARVEST_WEBSOCKET_PORT = os.environ.get('HARVEST_WEBSOCKET_PORT', 5000)
HARVEST_NEEDLE_SERVO_PIN = os.environ.get('HARVEST_NEEDLE_SERVO_PIN', 17)
HARVEST_POLE_SERVO_PIN = os.environ.get('HARVEST_POLE_SERVO_PIN', 27)
HARVEST_SLIDER_SERVO_PIN = os.environ.get('HARVEST_SLIDER_SERVO_PIN', 18)
HARVEST_EXTRUDER_SERVO_PIN = os.environ.get('HARVEST_EXTRUDER_SERVO_PIN', 22)
HARVEST_SMOKER_PIN = os.environ.get('HARVEST_SMOKER_PIN', 23)
HARVEST_PUMP_PIN = os.environ.get('HARVEST_PUMP_PIN', 24)


DATA_COLLECTION_METRICS = {
    'temperature': { 'base_value': 34.5, 'variance': 2, 'unit': '°C', 'anomaly_rate': 3 },
    'humidity': { 'base_value': 58, 'variance': 5, 'unit': '%', 'anomaly_rate': 1 },
    'co2': { 'base_value': 420, 'variance': 30, 'unit': 'ppm', 'anomaly_rate': 1 },
    'voc': { 'base_value': 2.1, 'variance': 0.3, 'unit': 'kΩ', 'anomaly_rate': 1 },
    'sound': { 'base_value': 68, 'variance': 5, 'unit': 'dB', 'anomaly_rate': 1 },
    'vibration': { 'base_value': 0.3, 'variance': 0.1, 'unit': 'mm/s', 'anomaly_rate': 1 },
    'bee_count': { 'base_value': 45000, 'variance': 2000, 'unit': '', 'anomaly_rate': 1 },
    'lux': { 'base_value': 1200, 'variance': 200, 'unit': 'lux', 'anomaly_rate': 1 },
    'uv_index': { 'base_value': 4, 'variance': 1, 'unit': '', 'anomaly_rate': 1 },
    'pheromone': { 'base_value': 85, 'variance': 10, 'unit': '', 'anomaly_rate': 1 },
    'odor_compounds': { 'base_value': None, 'variance': None, 'unit': '', 'anomaly_rate': 1 },
    'rainfall': { 'base_value': 0, 'variance': 0.5, 'unit': 'mm', 'anomaly_rate': 1 },
    'wind_speed': { 'base_value': 5, 'variance': 2, 'unit': 'km/h', 'anomaly_rate': 1 },
    'barometric_pressure': { 'base_value': 1013, 'variance': 5, 'unit': 'hPa', 'anomaly_rate': 1 },
    'image': { 'base_value': None, 'variance': None, 'unit': '', 'anomaly_rate': 0 },
    'pollen_concentration': { 'base_value': 65, 'variance': 15, 'unit': '', 'anomaly_rate': 1 },
    'activity': { 'base_value': None, 'variance': None, 'unit': '', 'anomaly_rate': 1 },
    'honey_harvested': { 'base_value': 200, 'variance': 100, 'unit': 'g', 'anomaly_rate': 0 }
}
