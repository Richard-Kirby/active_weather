import pigpio
import threading
import time
import sys
import subprocess
#import queue
import os
import json



class FanController(threading.Thread):

    # Initalise a given pin with a time delay.
    def __init__(self, fan_dict):

        threading.Thread.__init__(self)

        self.fan_dict = fan_dict

        '''
        This bit just gets the pigpiod daemon up and running if it isn't already.
        The pigpio daemon accesses the Raspberry Pi GPIO.  
        '''
        p = subprocess.Popen(['pgrep', '-f', 'pigpiod'], stdout=subprocess.PIPE)
        out, err = p.communicate()

        if len(out.strip()) == 0:
            os.system("sudo pigpiod")
            time.sleep(3)

        self.pi = pigpio.pi()

        self.pi.set_mode(fan_dict["fan_hall_effect_pin"], pigpio.INPUT)
        self.pi.set_pull_up_down(fan_dict["fan_hall_effect_pin"], pigpio.PUD_UP)

        #def cbf(gpio, level, tick):
        #print(gpio, level, tick)

        self.tacho_cb = self.pi.callback(fan_dict["fan_hall_effect_pin"], 0)

        #print("Starting up {} on pin {} with a duty of {} and time delay of {}" .format(self.name, self.fan_pin,
        #                                                                                self.duty, self.time_delay))

    # Over ride the run command which is what is run through as part of the thread.

    def run(self):

        try:
            target_rpm = 360
            gain = 0.01

            print(target_rpm, gain)
            current_pwm = 0


            while True:
                actual_rpm = self.tacho_cb.tally() * 30
                error = target_rpm - actual_rpm
                current_pwm = min(max(current_pwm + gain * error, 0), 255)

                print("Fan Pin {} Target {} PWM Cmd {:.2f} PWM % {:.2f} RPM {}".format(self.fan_dict["fan_cmd_pin"], target_rpm, current_pwm,
                                                                            current_pwm / 255 * 100, actual_rpm))
                self.tacho_cb.reset_tally()
                self.pi.set_PWM_dutycycle(self.fan_dict["fan_cmd_pin"], current_pwm)
                time.sleep(1)

        except KeyboardInterrupt:
            print("Keyboard interrupt")
            sys.exit(0)

        except:
            raise

        finally:
            pi.set_PWM_dutycycle(26, 0)
            pi.stop()



if __name__ == "__main__":

    fan_dict = {"fan_cmd_pin": 13,
                "fan_hall_effect_pin": 16,
                "fan_min_pwm": 0.20}

    fan_controller = FanController(fan_dict)

    fan_controller.start()






