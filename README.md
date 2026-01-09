# apiculture-iot

```
. /home/apiculture/apiculture-iot/setup.sh

. /home/apiculture/apiculture-iot/run_harvest_system.sh
tail -100f /home/apiculture/harvest.log

. /home/apiculture/apiculture-iot/run_data_collection_system.sh
tail -100f /home/apiculture/data_collection.log
```

```
pip3 install flask
pip3 install flask_socketio

source /home/apiculture/py_env/bme280_venv/bin/activate
source /home/apiculture/py_env/bme680_venv/bin/activate

pip3 install -r /home/apiculture/apiculture-iot/requirements.txt
pip3 install flask-socketio

export PYTHONPATH=/usr/lib/python3/dist-packages:$PYTHONPATH

python3 /home/apiculture/apiculture-iot/apiculture_iot/servo.py
python3 /home/apiculture/apiculture-iot/apiculture_iot/harvest.py
python3 /home/apiculture/apiculture-iot/apiculture_iot/camera.py
python3 /home/apiculture/apiculture-iot/apiculture_iot/pump_test.py
python3 /home/apiculture/apiculture-iot/apiculture_iot/smoker_test.py
python3 /home/apiculture/apiculture-iot/apiculture_iot/bme280_adafruit_reader2.py
```

```
# Raspberry pi 5

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
