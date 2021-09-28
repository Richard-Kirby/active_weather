import pigpio
import threading
import time
import sys
import subprocess
#import queue
import os
import json

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

pi.set_PWM_dutycycle(13, 0)
pi.set_mode(21, pigpio.INPUT)
pi.set_pull_up_down(21, pigpio.PUD_UP)

time.sleep(3)


tacho_cb = pi.callback(16, 0)


target_rpm = 360
current_pwm = 0
gain = 0.01


while True:
    actual_rpm = tacho_cb.tally() * 30
    error = target_rpm - actual_rpm
    current_pwm = min(max(current_pwm + gain * error, 0), 255)

    print("Target {} PWM Cmd {:.2f} PWM % {:.2f} RPM {}".format(target_rpm, current_pwm, current_pwm/255 * 100,actual_rpm))
    tacho_cb.reset_tally()
    pi.set_PWM_dutycycle(13, current_pwm)
    time.sleep(1)
'''

for i in range(0, 255):
    print("PWM Cmd {} PWM % {:.2f} RPM {}".format(i, i/255 * 100, tacho_cb.tally()*30))
    tacho_cb.reset_tally()
    pi.set_PWM_dutycycle(13, i)
    time.sleep(1)
'''

pi.set_PWM_dutycycle(13, 0)

time.sleep(5)

