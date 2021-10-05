import pigpio
import threading
import time
import sys
import subprocess
import queue
import os

import logging
# create logger
logger = logging.getLogger(__name__)


# Class that controls the misters via PWM.
class MistController(threading.Thread):

    # Initalise a given pin with a time delay.
    def __init__(self, mist_dict):

        threading.Thread.__init__(self)

        self.mist_dict = mist_dict
        self.mist_queue = queue.Queue()

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

        self.pi.set_mode(mist_dict["mister_pin"], pigpio.INPUT)

    # Accept commands for the fan(s) and check periodically for new commands coming in a queue
    def run(self):
        try:

            mist_pwm_ratio = 0

            while True:
                # Get the latest commanded RPM from the queue
                while not self.mist_queue.empty():
                    mist_pwm_ratio = self.mist_queue.get_nowait()
                    logger.debug("Mister Pin {} pwm {}".format(self.mist_dict["mister_pin"], int(mist_pwm_ratio*255)))
                    print("Mister Pin {} pwm {}".format(self.mist_dict["mister_pin"], int(mist_pwm_ratio*255)))

                self.pi.set_PWM_dutycycle(self.mist_dict["mister_pin"], int(mist_pwm_ratio * 255))
                time.sleep(2)

        except KeyboardInterrupt:
            logger.exception("Keyboard interrupt")

            # Todo: Can't get back to 0 RPM when shutdown by Ctrl-C
            self.pi.set_PWM_dutycycle(self.fan_dict["mister_pin"], 0)

        except:
            raise

        finally:
            # Todo: Can't get back to 0 RPM when shutdown by Ctrl-C
            self.pi.set_PWM_dutycycle(self.mist_dict["mister_pin"], 0)
            logger.error("finally")
            time.sleep(2)
            self.pi.stop()


if __name__ == "__main__":

    mist_dict_1 = {"mister_pin": 5}
    mist_dict_2 = {"mister_pin": 6}

    mist_controller_1 = MistController(mist_dict_1)
    mist_controller_2 = MistController(mist_dict_2)

    mist_controller_1.daemon = True
    mist_controller_1.start()

    mist_controller_2.daemon = True
    mist_controller_2.start()

    while True:
        for pwm_ratio in range(0, 11):
            mist_controller_1.mist_queue.put_nowait(float(pwm_ratio/10.0))
            mist_controller_2.mist_queue.put_nowait(float(pwm_ratio/10.0))
            time.sleep(5)

    exit(0)