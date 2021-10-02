import pigpio
import threading
import time
import sys
import subprocess
import queue
import os


# Class that controls computer fans via PWM.  This is for 4 pin fans, which have a PWM pin and hall effect pin for
# detecting fan speed.
class FanController(threading.Thread):

    # Initalise a given pin with a time delay.
    def __init__(self, fan_dict):

        threading.Thread.__init__(self)

        self.fan_dict = fan_dict
        self.rpm_queue = queue.Queue()
        self.gain = 0.015

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

    # Accept commands for the fan(s) and check periodically for new commands coming in a queue
    def run(self):
        try:
            target_rpm = 0
            current_pwm = 0

            while True:

                # Get the latest commanded RPM from the queue
                while not self.rpm_queue.empty():
                    target_rpm = self.rpm_queue.get_nowait()

                actual_rpm = self.tacho_cb.tally() * 30
                error = target_rpm - actual_rpm

                if target_rpm == 0:
                    current_pwm = 0
                else:
                    current_pwm = min(max(current_pwm + self.gain * error, int(fan_dict["fan_min_pwm"] *255)), 255)

                print("Fan Pin {} Target {} PWM Cmd {:.2f} PWM % {:.2f} RPM {}".format(self.fan_dict["fan_cmd_pin"], target_rpm, current_pwm,
                                                                                current_pwm / 255 * 100, actual_rpm))
                self.tacho_cb.reset_tally()
                self.pi.set_PWM_dutycycle(self.fan_dict["fan_cmd_pin"], current_pwm)
                time.sleep(1)

        except KeyboardInterrupt:
            print("Keyboard interrupt")

            # Todo: Can't get back to 0 RPM when shutdown by Ctrl-C
            self.pi.set_PWM_dutycycle(self.fan_dict["fan_cmd_pin"], 0)

        except:
            raise

        finally:
            # Todo: Can't get back to 0 RPM when shutdown by Ctrl-C
            self.pi.set_PWM_dutycycle(self.fan_dict["fan_cmd_pin"], 0)
            print("finally")
            time.sleep(2)
            self.pi.stop()


if __name__ == "__main__":

    fan_dict = {"fan_cmd_pin": 13,
                "fan_hall_effect_pin": 16,
                "fan_min_pwm": 0.15,
                "min_rpm": 200,
                "max_rpm": 2200}

    fan_controller = FanController(fan_dict)
    fan_controller.daemon = True

    fan_controller.start()

    while True:

        for target in range(200, 2600, 100):
            fan_controller.rpm_queue.put_nowait(target)
            time.sleep(5)

    exit(0)