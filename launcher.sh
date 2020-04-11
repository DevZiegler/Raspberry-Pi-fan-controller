#!/bin/sh
# launcher.sh

cd /home/pi/fan_control_pwm
sudo -u pi python3 fancontrol.py config.json fanlog.txt
