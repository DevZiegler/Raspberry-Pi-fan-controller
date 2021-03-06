# Raspberry-Pi-fan-controller
A pwm and temperature based voltage regulator circuit for controlling a fan with the Raspberry Pi with speedmeter (including the electronic circuit)

With this project it is possible to operate a 3-pin fan on the Raspberry PI voltage controlled.
The setting of the voltage is done by PWM, the duty cycle is set by a software PID controller. 
The electronic circuit is inverted, so the fan runs at full power when no PWM signal is present.
For monitoring, the speedometer of the fan is periodically evaluated by an interrupt routine.


## Installation
* Clone the repo
* Install PID Controller
```
 pip install simple-pid
```
* Make launcher.sh executable
```
 chmod +x launcher.sh
```

### Optional status plugin for LXPanel
Build LXPanel Plugin by yourself.
* Modify rpm.c, set the correct PATH
```
 line 10: #define PATH ".../rpm"
```
* Install dependencies
```
 sudo apt install lxpanel-dev
```
* Build plugin (run from lxpanel-rpm-plugin)
```
 gcc -Wall `pkg-config --cflags gtk+-2.0 lxpanel` -shared -fPIC rpm.c -o rpm.so `pkg-config --libs lxpanel`
```

Alternatively the already created plugin rpm.so can be used.
* Refresh frequency is set to 1 second
* Path is set to "/home/pi/Raspberry-Pi-fan-controller/rpm"


Copy the rpm.so into the LXPanel plugin directory.
```
 sudo cp rpm.so /usr/lib/arm-linux-gnueabihf/lxpanel/plugins/rpm.so
```
* Add to LXPanel


## Setup System
* Set parameter in config.json
```
{
    "pwm": {
        "pin": 24,             # Used GPIO in BCM scheme
        "frequency": 100,
        "maxDutyCycle": 31     # Maximum power-on time, inverted! 0 = full power, 100 = off
    },
    "speedometer": {
        "pin": 26              # Used GPIO in BCM scheme
    },
    "general": {
        "destTemp": 35,        # Target temperature in Celsius
        "maxTemp": 60,         # Maximum temperature at which the fan always runs at 100%
        "bufferSize": 10,      # How many old values are used for smoothing
        "checkFrequency": 10,  # Frequency of checking for a new config
        "sleepTime": 5,        # Time span in seconds between tests
        "pidAggressiveness": 1 # A higher value for a more aggressive PID controller
    "rpm": {
							   # Automatically filled at first start
    }
}
```
* Start luncher.sh once for the RPM calibration
* add luncher.sh to /etc/rc.local and reboot
```
 sudo nano /etc/rc.local
```

The circuit was designed with the help of the forum participants of [mikrocontroller.net](https://www.mikrocontroller.net/topic/492831) for a 5V/0.05A Fan.


![electronic circuit](/images/fan_control.png)
