#!/bin/bash

# Check if harvest.py is already running and kill it if so
if pgrep -f "harvest.py" > /dev/null; then
    echo "Previous harvest.py process found. Killing it..."
    pkill -f "harvest.py"
    sleep 2  # Brief pause to ensure cleanup
fi

# Activate the virtual environment
source /home/apiculture/py_env/bme280_venv/bin/activate

# Run the Python script
python3 /home/apiculture/apiculture-iot/apiculture_iot/harvest.py

# Optional: Deactivate the virtual environment after execution
# deactivate