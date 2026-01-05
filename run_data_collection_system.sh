#!/bin/bash

# Check if data_collection.py is already running and kill it if so
if pgrep -f "data_collection.py" > /dev/null; then
    echo "Previous data_collection.py process found. Killing it..."
    pkill -f "data_collection.py"
    sleep 2  # Brief pause to ensure cleanup
fi

# Activate the virtual environment
source /home/apiculture/py_env/bme280_venv/bin/activate

# Run the Python script in the background with nohup for detachment
nohup python3 /home/apiculture/apiculture-iot/apiculture_iot/data_collection.py > /home/apiculture/data_collection.log 2>&1 &

# Optional: Store the PID for later reference
echo $! > /home/apiculture/data_collection.pid

echo "data_collection.py started in the background. PID: $!. Check log at /home/apiculture/data_collection.log"

# Deactivate the virtual environment (optional, since script exits)
deactivate