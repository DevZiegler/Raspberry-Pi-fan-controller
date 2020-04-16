#!/bin/sh
# launcher.sh

cd /home/pi/Raspberry-Pi-fan-controller
sudo -u pi python3 fancontrol.py config.json fanlog.log
