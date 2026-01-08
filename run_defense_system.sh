#!/bin/bash

# Check if defense.py is already running and kill it if so
if pgrep -f "defense.py" > /dev/null; then
    echo "Previous defense.py process found. Killing it..."
    pkill -f "defense.py"
    sleep 2  # Brief pause to ensure cleanup
fi

# Activate the virtual environment
source /home/apiculture/py_env/bme280_venv/bin/activate

# Run the Python script in the background with nohup for detachment
nohup python3 /home/apiculture/apiculture-iot/apiculture_iot/defense.py > /home/apiculture/defense.log 2>&1 &

# Optional: Store the PID for later reference
echo $! > /home/apiculture/defense.pid

echo "defense.py started in the background. PID: $!. Check log at /home/apiculture/defense.log"

# Deactivate the virtual environment (optional, since script exits)
deactivate