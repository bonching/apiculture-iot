#!/bin/bash

# Update and upgrade the system packages
sudo apt update

sudo apt install python3-setuptools python3-wheel
sudo apt install python3-picamzero -y
sudo apt install python3-gpiozero -y

# Add PYTHONPATH export to .bashrc
echo 'export PYTHONPATH=/usr/lib/python3/dist-packages:$PYTHONPATH' >> ~/.bashrc
source ~/.bashrc

# Create the project directory
mkdir -p /home/apiculture/py_env

# Create and activate the BME280 virtual environment
python3 -m venv /home/apiculture/py_env/bme280_venv
source /home/apiculture/py_env/bme280_venv/bin/activate

# Install the required packages for BME280
sudo pip3 install adafruit-blinka adafruit-circuitpython-busdevice adafruit-circuitpython-bme280

# Re-install system packages (as specified, even if redundant)
sudo pip3 install RPi.GPIO
sudo pip3 install -r /home/apiculture/apiculture-iot/requirements.txt

echo "Setup complete! Virtual environment 'bme280_venv' is activated. Run 'deactivate' to exit when done."