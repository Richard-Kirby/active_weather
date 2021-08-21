import pigpio
import time
import sys
import subprocess
import os

"""
This bit just gets the pigpiod daemon up and running if it isn't already.
The pigpio daemon accesses the Raspberry Pi GPIO.  
"""
p = subprocess.Popen(['pgrep', '-f', 'pigpiod'], stdout=subprocess.PIPE)
out, err = p.communicate()

if len(out.strip()) == 0:
    os.system("sudo pigpiod")
    time.sleep(3)

pi = pigpio.pi()

while True:
    for pwm in range (0,255):
        print("PWM", pwm)
        pi.set_PWM_dutycycle(5, pwm)   
        pi.set_PWM_dutycycle(6, pwm)
        time.sleep(1)

