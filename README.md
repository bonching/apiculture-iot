# apiculture-iot

## Configure the Raspberry Pi (one time setup)
```
. /home/apiculture/apiculture-iot/setup.sh
```
---

### Run the IoT agent (Harvest system)
```
. /home/apiculture/apiculture-iot/run_harvest_system.sh
tail -100f /home/apiculture/harvest.log
```

### Run the IoT agent (Data collection system)
```
. /home/apiculture/apiculture-iot/run_data_collection_system.sh
tail -100f /home/apiculture/data_collection.log
```

### Run the IoT agent (Defense system)
```
. /home/apiculture/apiculture-iot/run_defense_system.sh
tail -100f /home/apiculture/defense.log
```
---

## Raspberry pi 5 setup
```

```



### Other commands
```
pip3 install flask
pip3 install flask_socketio

source /home/apiculture/py_env/bme280_venv/bin/activate
source /home/apiculture/py_env/bme680_venv/bin/activate

pip3 install -r /home/apiculture/apiculture-iot/requirements.txt
pip3 install flask-socketio

export PYTHONPATH=/usr/lib/python3/dist-packages:$PYTHONPATH

python3 /home/apiculture/apiculture-iot/apiculture_iot/servo_angle_test.py 18 45
python3 /home/apiculture/apiculture-iot/apiculture_iot/servo_rotate_test.py 22 5
python3 /home/apiculture/apiculture-iot/apiculture_iot/servo_SG90_calibrate.py
python3 /home/apiculture/apiculture-iot/apiculture_iot/harvest.py
python3 /home/apiculture/apiculture-iot/apiculture_iot/camera.py
python3 /home/apiculture/apiculture-iot/apiculture_iot/pump_test.py
python3 /home/apiculture/apiculture-iot/apiculture_iot/smoker_test.py
python3 /home/apiculture/apiculture-iot/apiculture_iot/solenoid_valve_test.py
python3 /home/apiculture/apiculture-iot/apiculture_iot/bme280_adafruit_reader2.py
```


```
sudo apt purge python3-gpiozero
sudo apt update
sudo apt install python3-gpiozero

dpkg -l | grep gpiozero

source /home/apiculture/py_env/bme280_venv/bin/activate
pip3 uninstall gpiozero
pip3 install gpiozero

/usr/bin/python3 -c "import gpiozero; print(gpiozero.__version__)"



sudo apt update --allow-releaseinfo-change
sudo apt --fix-broken install --allow-downgrades
```
