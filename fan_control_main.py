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

pi.set_PWM_dutycycle(26, 255)
pi.set_mode(21, pigpio.INPUT)
pi.set_pull_up_down(21, pigpio.PUD_UP)


def cbf(gpio, level, tick):
   print(gpio, level, tick)

tacho_cb = pi.callback(21, 0)

class FanControl(threading.Thread):

    # Initalise a given pin with a time delay.
    def __init__(self, name, rpi, fan_pin, duty=255, duration= 300, time_delay=3600):

        threading.Thread.__init__(self)

        self.pi = rpi  # Pi it is being run on

        print(self.pi)

        self.name = name  # Name of the fan controller
        self.fan_pin = fan_pin  # pin to use

        # Set duty after checking it makes sense.
        if 0 <= duty <= 255:
            self.duty = duty
        else:
            self.duty = 255

        self.duration = duration  # how long to turn the fan on for.
        self.time_delay = time_delay  # how long to turn the fan off for.

        print("Starting up {} on pin {} with a duty of {} and time delay of {}" .format(self.name, self.fan_pin,
                                                                                        self.duty, self.time_delay))

    # Over ride the run command which is what is run through as part of the thread.

    def run(self):

        # Run forever using the parameters provided.
        try:
            while True:
                print("{} pin {} ON for {}" .format(self.name, self.fan_pin,  self.duration))
                pi.set_PWM_dutycycle(self.fan_pin, self.duty)
                time.sleep(self.duration)
                print("{} pin {} OFF for {}".format(self.name, self.fan_pin, self.time_delay))
                pi.set_PWM_dutycycle(self.fan_pin, 0)
                time.sleep(self.time_delay)

        except:
            pi.set_PWM_dutycycle(self.fan_pin, 0)
            raise


# Set up a few fan controllers such that there are some to choose from.

try:
    target_rpm = 360
    gain = 0.01

    print(target_rpm, gain)
    current_pwm = 0

    while True:
        actual_rpm = tacho_cb.tally() * 30
        error = target_rpm - actual_rpm
        current_pwm = min(max(current_pwm + gain * error,0), 255)

        print("Target {} PWM Cmd {:.2f} PWM % {:.2f} RPM {}".format(target_rpm, current_pwm, current_pwm/255 * 100,actual_rpm))
        tacho_cb.reset_tally()
        pi.set_PWM_dutycycle(26, current_pwm)
        time.sleep(1)


    for i in range(0, 255):
        print("PWM Cmd {} PWM % {:.2f} RPM {}".format(i, i/255 * 100, tacho_cb.tally()*30))
        tacho_cb.reset_tally()
        pi.set_PWM_dutycycle(26, i)
        time.sleep(1)

    pi.set_PWM_dutycycle(26,0)



    time.sleep(5)

    fan_control1 = FanControl("Every 2 minutes(test)", pi, 26, duty=100, duration=120, time_delay=120)
    fan_control1.daemon = True
    fan_control1.start()

    fan_control2 = FanControl("Every hour", pi, 20, duty=255, duration=120, time_delay=60*60)
    fan_control2.daemon = True
    fan_control2.start()

    fan_control3 = FanControl("Every 2 hours", pi, 16, duty=255, duration=120, time_delay=60*60*2)
    fan_control3.daemon = True
    fan_control3.start()

    fan_control4 = FanControl("Every 4 hours", pi, 27, duty=255, duration=120, time_delay=60*60*4)
    fan_control4.daemon = True
    fan_control4.start()

    fan_control5 = FanControl("Every 8 hours", pi, 19, duty=255, duration=120, time_delay=60*60*8)
    fan_control5.daemon = True
    fan_control5.start()






    while True:
        pass


except KeyboardInterrupt:
    print("Keyboard interrupt")
    sys.exit(0)

except:
    raise

finally:
    pi.set_PWM_dutycycle(26, 0)
    pi.stop()





