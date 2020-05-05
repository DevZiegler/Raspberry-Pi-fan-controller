#!/usr/bin/env python3
import os
import os.path
import sys
import json
import math
import pprint
import logging
import datetime
import traceback
from time import sleep
import RPi.GPIO as GPIO
from simple_pid import PID
from logging.handlers import RotatingFileHandler


def getCPUtemperature():
    res = os.popen('vcgencmd measure_temp').readline()
    temp = (res.replace("temp=", "").replace("'C\n", ""))
    return float(temp)

def fanOFF(PWMController):
    PWMController.ChangeDutyCycle(100)  # switch fan off
    # todo: disable power circuit!
    
def fanON(PWMController):
    PWMController.ChangeDutyCycle(0)  # switch fan on
    # todo: enable power circuit!

def countInterrupt(Channel):
    global interruptCounter
    interruptCounter += 1

def millis_interval(start, end):
    diff = end - start
    millis = diff.days * 24 * 60 * 60 * 1000
    millis += diff.seconds * 1000
    millis += diff.microseconds / 1000
    return millis

def getRPM():
    global lastRPMAccessTime
    global interruptCounter
    currentCounter = interruptCounter
    interruptCounter = 0
    currentTime = datetime.datetime.now()
    timespanInSeconds = millis_interval(lastRPMAccessTime, currentTime)
    calcRPM = int(currentCounter / timespanInSeconds * 60000)
    lastRPMAccessTime = currentTime
    return calcRPM

def emergencyMode(PWMController):
    fanOFF(PWMController)
    output('!*!*!*!*! Run emergency mode, turn Fan off', 2)            
    with open("rpm", "w") as f:
        f.write("ERROR")
    while True:
        sleep(10)
        output('!*!*!*!*! Run emergency mode, turn Fan off', 2)
        if os.path.isfile('restart'):
            os.remove('restart')
            output('!*!*!*!*! restart Fan', 0)
            fanON(PWMController)
            sleep(1)
            break


def output(text, lvl=0):    
    if lvl == 0:
        myLog.info(text)
    if lvl == 1:
        myLog.warning(text)
    if lvl == 2:
        myLog.error(text)
    if lvl == 3:
        myLog.exception(text)



# internal var section
dutyCycle = 0
interruptCounter = 0
lastRPMAccessTime = None
maxTempExceeded = False
useBuffer = True
pidBuffer = list()
# arguments
configFile = sys.argv[1]
logFile = sys.argv[2]
# from config
diffTemp = None
sleepTime = None
checkFrequency = None

logging.basicConfig(format='%(asctime)s %(levelname)-8s %(message)s',
                    level=logging.INFO,
                    datefmt='%Y-%m-%d %H:%M:%S')
                    
myLog = logging.getLogger("Rotationg log")
myLog.setLevel(logging.INFO)
handler = RotatingFileHandler(logFile, maxBytes=51200, backupCount=5)
myLog.addHandler(handler)

output("StartUp with parameters '[%s,%s]'" % (configFile, logFile))


def loadConfig():
    global configFile
    with open(configFile) as json_data_file:
        configData = json.load(json_data_file)
    return configData

output("load inital config")
config = loadConfig()
output(pprint.pformat(config))


def setupEvironment(configData):
    global dutyCycle
    global diffTemp
    global lastRPMAccessTime
    global sleepTime
    global pidBuffer
    global maxTempExceeded
    global useBuffer
    global checkFrequency
    
    output("setup new evironment")
    GPIO.cleanup() 
    dutyCycle=0
    
    output("setup pid-controller")
    pid = PID(configData['general']['pidAggressiveness'], 0.01, 0.1, setpoint=configData['general']['destTemp'])
    pid.output_limits = (0, configData['pwm']['maxDutyCycle'])
    
    output("setup gpio")
    #pwn
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(configData['pwm']['pin'], GPIO.OUT)
    myPWM = GPIO.PWM(configData['pwm']['pin'], configData['pwm']['frequency'])
    myPWM.start(dutyCycle)
    # interrupt detection
    lastRPMAccessTime = datetime.datetime.now()
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(configData['speedometer']['pin'], GPIO.IN)
    GPIO.remove_event_detect(configData['speedometer']['pin'])
    GPIO.add_event_detect(configData['speedometer']['pin'], GPIO.FALLING, callback=countInterrupt)
    GPIO.setwarnings(False)
    
    diffTemp = configData['general']['maxTemp']-configData['general']['destTemp']
    sleepTime = configData['general']['sleepTime']
    checkFrequency = configData['general']['checkFrequency']
    pidBuffer = list()    
    maxTempExceeded = False
    useBuffer = True    
    return myPWM, pid

def checkRPMSection(PWMController, configData):
    # Check if RPM section total filled
    newData = False
    for i in range(configData['pwm']['maxDutyCycle']+1):
        if str(i) not in configData['rpm']:
            output("No RPM bounds found for dutyCycle '%s'" % i)
            newData = True
            PWMController.ChangeDutyCycle(i)
            sleep(5)
            getRPM()
            sleep(10)
            configData['rpm'][str(i)] = int(getRPM())
            output('%s RPM were measured' % configData['rpm'][str(i)],0)

    if newData:
        with open(configFile, 'w') as outfile:
            json.dump(configData, outfile)
        output('!!!NEW RPM bounds written to config file!!!',1)
        output('Check it and restart the Program!',1)
        fanOFF(PWMController)
        GPIO.cleanup()  # resets all GPIO ports used by this program
        exit(1)

if __name__ == '__main__':
    try:
        pwmController, pidController = setupEvironment(config)
        checkRPMSection(pwmController, config)
        
        # Main program loop        
        errorCount = 0
        configCheck = 0
        getRPM()
        while True:
            sleep(sleepTime)

            configCheck+=1
            disableRPMCheck = False
            if configCheck == checkFrequency:
                configCheck = 0
                newConfig = loadConfig()
                if newConfig != config:
                    config = newConfig
                    output("new config loaded")
                    output(pprint.pformat(config))
                    pwmController = None
                    pwmController, pidController = setupEvironment(config)
                    sleep(2)
                    checkRPMSection(pwmController, config)
                    disableRPMCheck = True

            if not disableRPMCheck:
                # Check RPM for error
                currentRPM = getRPM()
                
                lowerDC = math.floor(dutyCycle)
                upperDC = min(config['pwm']['maxDutyCycle'], math.floor(dutyCycle)+1)
                lowerRPM = config['rpm'][str(lowerDC)]
                upperRPM = config['rpm'][str(upperDC)]
                
                expectedRPM = int(lowerRPM + ((upperRPM - lowerRPM) * (dutyCycle - lowerDC)))
                upperBounder = expectedRPM + 600.0
                lowerBounder = expectedRPM - 600.0
                
                if upperBounder < currentRPM or currentRPM < lowerBounder:
                    output('RPM not in boundary: current dutyCycle "%s", measured RPM "%s", expected RPM "%s", upper RPM "%s", lower RPM "%s" ' % (dutyCycle, currentRPM, expectedRPM, upperBounder, lowerBounder),1)
                    if errorCount >= 5:
                        emergencyMode(pwmController)
                        errorCount = 0
                    errorCount+=1
                else:
                    errorCount = 0
            else:
                disableRPMCheck = False

            # Change PWM frequency
            useBuffer = True
            currentTemp = getCPUtemperature()
            newDutyCycle = dutyCycle
            pid_temp = max(0, config['general']['destTemp'] * ((config['general']['maxTemp']-currentTemp) / diffTemp))
            currentDutyCycle = config['pwm']['maxDutyCycle'] - pidController(pid_temp)
            currentDutyCycle = round(currentDutyCycle, 1)
            
            if currentTemp >= config['general']['maxTemp']:
                maxTempExceeded = True
            
            if maxTempExceeded:
                if currentTemp <= config['general']['maxTemp']-10:
                    maxTempExceeded = False
                currentDutyCycle = 0
                useBuffer = False
            else:
                diff = currentDutyCycle - dutyCycle
                if diff > 6:
                    currentDutyCycle = dutyCycle + 6
                elif diff < -2:
                    useBuffer = False

            if errorCount > 2:
                currentDutyCycle = 0
            
            pidBuffer.append(currentDutyCycle)

            if len(pidBuffer) > config['general']['bufferSize']:
                pidBuffer.pop(0)
            if useBuffer:
                newDutyCycle = round((sum(pidBuffer) / len(pidBuffer)), 1)
            else:
                newDutyCycle = currentDutyCycle
                for i in range(int(config['general']['bufferSize']/2)):
                    pidBuffer.append(currentDutyCycle)
                    pidBuffer.pop(0)
                    
                    
            oldDutyCycle = dutyCycle
            if newDutyCycle != dutyCycle:
                dutyCycle = max(min(newDutyCycle,config['pwm']['maxDutyCycle']),0)
                pwmController.ChangeDutyCycle(dutyCycle)
            output("Temp: '%s'; next DC '%.1f' ; pid DC '%.1f' ; old DC '%.1f' (measured RPM '%d', expected RPM '%d')" % (currentTemp, dutyCycle, currentDutyCycle, oldDutyCycle, currentRPM, expectedRPM),0)
            with open("rpm", "w") as f:
                f.write(str(currentRPM))
            
            
    except KeyboardInterrupt:
        fanOFF(pwmController)
        GPIO.cleanup()  # resets all GPIO ports used by this program
        output("KeyboardInterruption, exit program",0)

    except Exception:
        output('Unkown error! Exit program',4)
        fanOFF(pwmController)
        GPIO.cleanup()  # resets all GPIO ports used by this program
        traceback.print_exc()
    finally:  
        GPIO.cleanup() # this ensures a clean exit 

