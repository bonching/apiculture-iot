#!/bin/bash

# Check if harvest.py is already running and kill it if so
if pgrep -f "harvest.py" > /dev/null; then
    echo "Previous harvest.py process found. Killing it..."
    pkill -f "harvest.py"
    sleep 2  # Brief pause to ensure cleanup
fi

# Activate the virtual environment
source /home/apiculture/py_env/bme280_venv/bin/activate

cd /home/apiculture/apiculture-iot/

# Run the Python script in the background with nohup for detachment
nohup python3 /home/apiculture/apiculture-iot/apiculture_iot/harvest.py > /home/apiculture/harvest.log 2>&1 &

cd ~

# Optional: Store the PID for later reference
echo $! > /home/apiculture/harvest.pid

echo "harvest.py started in the background. PID: $!. Check log at /home/apiculture/harvest.log"

# Deactivate the virtual environment (optional, since script exits)
deactivate