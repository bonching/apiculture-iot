#!/bin/bash

# Update and upgrade the system packages
sudo apt update

sudo apt install python3.11-dev -y
sudo apt install python3-setuptools python3-wheel -y
sudo apt install python3-picamzero -y
sudo apt install python3-gpiozero -y
sudo apt install python3-rpi.gpio
#sudo apt install rpi-connect -y # causing ssh failure

# install desktop
#sudo apt install raspberrypi-ui-mods lightdm xserver-xorg arandr -y
#sudo systemctl set-default graphical.target

# Add PYTHONPATH export to .bashrc
echo 'export PYTHONPATH=/usr/lib/python3/dist-packages:$PYTHONPATH' >> ~/.bashrc
source ~/.bashrc

# Create the project directory
mkdir -p /home/apiculture/py_env

# Create and activate the BME280 virtual environment
# deactivate
# rm -rf /home/apiculture/py_env/bme280_venv
python3 -m venv /home/apiculture/py_env/bme280_venv
source /home/apiculture/py_env/bme280_venv/bin/activate
pip3 install --upgrade pip setuptools wheel
# pip3 cache purge
# rm -rf ~/.cache/pip

# Re-install system packages (as specified, even if redundant)
pip3 install RPi.GPIO

# Install the required packages for BME280
pip3 install --force-reinstall --no-deps --no-cache-dir adafruit-blinka
pip3 install --force-reinstall --no-deps --no-cache-dir adafruit-circuitpython-busdevice
pip3 install --force-reinstall --no-deps --no-cache-dir adafruit-circuitpython-bme280
pip3 install --force-reinstall --no-deps --no-cache-dir adafruit-platformdetect


# pip3 install -r /home/apiculture/apiculture-iot/requirements.txt
pip3 install flask flask-socketio python-socketio gpiozero picamera2 requests
pip3 install python-dateutil pymongo

echo "Setup complete! Virtual environment 'bme280_venv' is activated. Run 'deactivate' to exit when done."