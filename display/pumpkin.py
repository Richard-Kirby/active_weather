#!/usr/bin/python3
# -*- coding: UTF-8 -*-

''' Pumpkin

A bit of a hacked together jack o lantern controller
'''

import logging.config

# create logger
log_dict = {
    'version': 1,
    'formatters': {
        'detailed': {
            'class': 'logging.Formatter',
            'format': '%(asctime)s %(name)-15s %(levelname)-8s %(processName)-10s %(message)s'
        }
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'level': 'INFO',
        },
        'file': {
            'class': 'logging.FileHandler',
            'filename': 'mplog.log',
            'mode': 'w',
            'formatter': 'detailed',
        },
        'foofile': {
            'class': 'logging.FileHandler',
            'filename': 'mplog-foo.log',
            'mode': 'w',
            'formatter': 'detailed',
        },
        'errors': {
            'class': 'logging.FileHandler',
            'filename': 'mplog-errors.log',
            'mode': 'w',
            'level': 'ERROR',
            'formatter': 'detailed',
        },
    },
    'loggers': {
        'foo': {
            'handlers': ['foofile']
        }
    },
    'root': {
        'level': 'DEBUG',
        'handlers': ['console', 'file', 'errors']
    },
}

logging.config.dictConfig(log_dict)

# create file handler which logs even debug messages
logger = logging.getLogger(__name__)


from fan_control import FanController
from mist_control import MistController
from led_strip_control import LedStripControl
import time
import threading
import queue

import rpi_ws281x
import logging

# create logger
logger = logging.getLogger(__name__)

# Clock Display Class - takes care of the display.
class Pumpkin(threading.Thread):

    # Initialising - set up the display, fonts, etc.
    def __init__(self):
        threading.Thread.__init__(self)

        # Create a Fan Controller to control the computer fans
        fan_dict = {"fan_cmd_pin": 13,
                    "fan_hall_effect_pin": 16,
                    "fan_min_pwm": 0.15,
                    "min_rpm": 200,
                    "max_rpm": 2200}

        self.fan_controller = FanController(fan_dict)
        self.fan_controller.daemon = True

        self.fan_controller.start()


        # Set up mist controllers
        mist_dict_1 = {"mister_pin": 5}
        mist_dict_2 = {"mister_pin": 6}

        self.mist_controllers= [MistController(mist_dict_1), MistController(mist_dict_2)]

        for mister in self.mist_controllers:
            mister.daemon = True
            mister.start()


        # LED strip configuration - NOTE: Using a lot of defaults from the library, frequency, DMA channel, etc.
        LED_COUNT = 180  # Number of LED pixels.
        LED_PIN = 18  # GPIO pin connected to the pixels (must support PWM!).

        # Set up the LED Display
        self.led_display = LedStripControl(LED_COUNT, LED_PIN)

        self.led_display.pixel_clear()

        time.sleep(4)

        logger.debug("LED Object init")
        self.led_display.daemon = True
        self.led_display.start()
        logger.debug("Pumpkin init")

    # Set Fan Speed according to a ratio.
    def set_fan_speed(self, ratio):

        if ratio is 0:
            rpm = 0
        else:
            rpm = int((max(0, min(ratio, 1))) * float (self.fan_controller.fan_dict["max_rpm"]
                                                   - self.fan_controller.fan_dict["min_rpm"])
                  + self.fan_controller.fan_dict["min_rpm"])

        logger.debug("Fan RPM {}" .format(rpm))

        self.fan_controller.rpm_queue.put_nowait(int(rpm))

    # Set the LED Strip.
    def set_strip(self, pixels_to_display, colour):
        #logger.debug("Number of pixels {}".format(pixels_to_display))

        pixels = []
        for i in range(pixels_to_display):
            pixels.append(colour)

        self.led_display.incoming_queue.put_nowait(pixels)

    # Main process of the thread.  Waits for the criteria to be reached for the displaying on the screen.
    def run(self):

        while True:

            self.set_fan_speed(0)
            self.mist_controllers[0].mist_queue.put_nowait(1)
            self.mist_controllers[1].mist_queue.put_nowait(1)

            for i in range(50,255,20):
                self.set_strip(180, rpi_ws281x.Color(i, 0, 0))
                time.sleep(1)
            #self.set_strip(180, rpi_ws281x.Color(50, 0, 0))
            #time.sleep(2)

            #self.set_strip(180, rpi_ws281x.Color(255, 0, 255))

            time.sleep(10)

            self.set_strip(180, rpi_ws281x.Color(255,255, 102))
            self.mist_controllers[0].mist_queue.put_nowait(1.0)
            self.mist_controllers[1].mist_queue.put_nowait(1.0)
            self.set_fan_speed(0.3)
            time.sleep(5)

            self.set_strip(180, rpi_ws281x.Color(0, 100, 0))
            self.set_fan_speed(0.2)
            time.sleep(5)

            self.set_strip(180, rpi_ws281x.Color(255,153,51))
            self.mist_controllers[0].mist_queue.put_nowait(1)
            self.mist_controllers[1].mist_queue.put_nowait(1)
            self.set_fan_speed(0)
            time.sleep(5)


if __name__ == '__main__':
    pumpkin = Pumpkin()
    pumpkin.daemon = True
    pumpkin.start()

    while True:
        logger.debug("Pumpkin Running")
        time.sleep(15)
