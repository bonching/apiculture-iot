#!/bin/bash
# Cleanup function
cleanup() {
    sudo pinctrl set 18 ip pn  # Reset to input
    exit 0
}
trap cleanup SIGINT SIGTERM

# Set as output
sudo pinctrl set 18 op pn

while true; do
    sudo pinctrl set 18 dh
    echo "LED ON"
    sleep 1
    sudo pinctrl set 18 dl
    echo "LED OFF"
    sleep 1
done