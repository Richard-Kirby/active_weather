#!/usr/bin/python
# -*- coding: UTF-8 -*-
#import chardet
import os
import sys 
import time

import spidev as SPI
import rpi_ws281x
import time
import threading
import queue
import colorsys

from .lib import LCD_1inch28 # Using the round 240 x 240 pixel Waveshare round display
from PIL import Image, ImageDraw, ImageFont
from .fan_control import FanController
from .mist_control import MistController
from .led_strip_control import LedStripControl

import logging
# create logger
logger = logging.getLogger(__name__)

# Raspberry Pi pin configuration:
RST = 27
DC = 25
BL = 23
bus = 0 
device = 0 

icon_dict = {
    "Clear" :   {"icon":'./display/icons/Sunny.png', "mist": 0},
    "Sunny" :   {"icon":'./display/icons/Sunny.png', "mist": 0},
    "PrtCld":   {"icon":'./display/icons/PrtCld.png',"mist": 0.4},
    "PrtCLd":   {"icon":'./display/icons/PrtCld.png', "mist": 0.4},
    "Not used": {"icon":'./display/icons/weather_vane.png',"mist": 0},
    "Mist":     {"icon":'./display/icons/weather_vane.png',"mist": 0.6},
    "Fog":      {"icon":'./display/icons/weather_vane.png',"mist": 0.6},
    "Cloudy":   {"icon":'./display/icons/Cloudy.png',"mist": 0.6},
    "Overcst":  {"icon":'./display/icons/Overcst.png',"mist": 1},
    "L rain":   {"icon":'./display/icons/L_rain.png', "mist": 1}, # "Light rain shower (night)",
    "L shwr":   {"icon":'./display/icons/L_shwr.png', "mist": 0.6},  # Light rain shower (day)",
    "Drizzl":   {"icon":'./display/icons/weather_vane.png',"mist": 1},
    "L rain":   {"icon":'./display/icons/L_rain.png', "mist": 1}, # "Light rain",
    "Hvy sh":   {"icon":'./display/icons/H_rain.png', "mist": .6}, # "Heavy rain shower (night)",
    "Hvy sh":   {"icon":'./display/icons/H_rain.png', "mist": .6}, # "Heavy rain shower (day)",
    "H rain":   {"icon":'./display/icons/H_rain.png', "mist": 1},
    "Slt sh":   {"icon":'./display/icons/weather_vane.png', "mist": 0.6}, # "Sleet shower (night)",
    "Slt sh":   {"icon":'./display/icons/weather_vane.png', "mist": 0.6},# "Sleet shower (day)",
    "Sleet":    {"icon":'./display/icons/weather_vane.png', "mist": 0.6},
    "Hail sh":  {"icon":'./display/icons/weather_vane.png', "mist": 0.6}, # Hail shower (night)",
    "Hail sh":  {"icon":'./display/icons/weather_vane.png', "mist": 0.6},  # "Hail shower (day)",
    "Hail":     {"icon": './display/icons/weather_vane.png', "mist": 0.6},
    "L snw sh": {"icon": './display/icons/weather_vane.png', "mist": 0.6}, # "Light snow shower (night)",
    "L snw sh": {"icon": './display/icons/weather_vane.png', "mist": 0.6}, # "Light snow shower (day)",
    "L snw":    {"icon": './display/icons/weather_vane.png', "mist": 1},
    "H snw sh": {"icon": './display/icons/weather_vane.png', "mist": 0.6}, # "Heavy snow shower (night)",
    "H snw sh": {"icon": './display/icons/weather_vane.png', "mist": 0.6},  # "Heavy snow shower (day)",
    "H snw":    {"icon": './display/icons/weather_vane.png', "mist": 1.0},
    "Thndr sh": {"icon": './display/icons/weather_vane.png',"mist": 0.6},  # "Thunder shower (night)",
    "Thndr sh": {"icon": './display/icons/weather_vane.png',"mist": 0.6},  # "Thunder shower (day)",
    "Thndr":    {"icon": './display/icons/weather_vane.png', "mist": 1}
}

min_wind_speed = 3 # 0 RPM below this in mph.
max_wind_speed = 25  # maximum fan output above this in mph.


# Clock Display Class - takes care of the display.
class ClockDisplay(threading.Thread):

    # Initialising - set up the display, fonts, etc.
    def __init__(self):
        threading.Thread.__init__(self)

        # Display Set up.
        self.disp = LCD_1inch28.LCD_1inch28()

        # Initialize library.
        self.disp.Init()

        # Clear display.
        self.disp.clear()

        main_font = './display/HammersmithOne-Regular.ttf'

        self.date_font = ImageFont.truetype(main_font, 20)
        self.time_font = ImageFont.truetype(main_font, 40)
        self.location_font = ImageFont.truetype(main_font, 30)
        self.status_font = ImageFont.truetype(main_font, 20)

        # Queue to receive time updates.
        self.time_queue = queue.Queue()

        # Queue and Variable for Met Office 5 day forecast
        self.weather_text = ""
        self.met_forecast_queue = queue.Queue()
        self.five_day_forecast = None

        # Create a Fan Controller to simulate wind.
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

        # temperature settings
        self.min_temp = -40
        self.max_temp = 49
        self.thermo_pixel_count = 90

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
        logger.debug("Clock Display init")

    # Handle the status update from the Met Office.
    def handle_met_status(self):

        # old code for ref
        #weather_icon = Image.open('./display/icons/weather_vane.png')
        #self.image.paste(weather_icon, (56, 56))
        #self.draw = ImageDraw.Draw(self.image)

        # Get most recent weather status.
        if not self.met_forecast_queue.empty():
            while not self.met_forecast_queue.empty():
                self.five_day_forecast = self.met_forecast_queue.get_nowait()

        # Create a string for the current forecast
        if self.five_day_forecast is not None and len(self.five_day_forecast) == 5:
            degree_sign = u"\N{DEGREE SIGN}"

            self.weather_text = [self.five_day_forecast[0]['date'][:3],

                                 "{} {}{}C {}%".format(
                                self.five_day_forecast[0]['day_weather_type'],
                                self.five_day_forecast[0]['high_temp'], degree_sign,
                                self.five_day_forecast[0]['prob_ppt_day']),

                            "{} {}{}C {}%".format(
                                self.five_day_forecast[0]['night_weather_type'],
                                self.five_day_forecast[0]['low_temp'], degree_sign,
                                self.five_day_forecast[0]['prob_ppt_night']),

                            "Wind {}mph".format(self.five_day_forecast[0]["wind_speed_day"])
                            ]

            #logger.debug("Day wind speed {} mph" .format(self.five_day_forecast[0]['wind_speed_day']))

            # fan commanded here to set the wind speed
            self.set_fan_speed_from_wind_speed(int(self.five_day_forecast[0]["wind_speed_day"]))
            #self.set_mist_from_forecast(icon_dict[self.five_day_forecast[0]["day_weather_type"]]['mist'])
            logger.debug("{} mist {}".format(self.five_day_forecast[0]["day_weather_type"],
                                             icon_dict[self.five_day_forecast[0]["day_weather_type"]]['mist']))

            for mister in self.mist_controllers:
                mister.mist_queue.put_nowait(icon_dict[self.five_day_forecast[0]["day_weather_type"]]['mist'])

            # Set the thermometer colours
            logger.debug("Temp to display on LED strip {}".format(self.five_day_forecast[0]['high_temp']))
            self.set_thermometer_display(int(self.five_day_forecast[0]['high_temp']))

        # Weather Text drawn here.
        if len(self.weather_text) > 0:

            #logger.debug(self.five_day_forecast[0]['day_weather_type'])

            icon_img = icon_dict[self.five_day_forecast[0]['day_weather_type']]['icon']

            weather_icon = Image.open(icon_img)
            self.image.paste(weather_icon, (88, 155))
            self.draw = ImageDraw.Draw(self.image)

            fc_size = []

            vert_loc = [80]
            day_hor = 20

            for i in range(1, len(self.weather_text)):
                txt_size = self.status_font.getsize(self.weather_text[i-1])
                vert_loc.append(vert_loc[i-1] + txt_size[1] + txt_size[1]/4)

            fore_hor = day_hor + self.status_font.getsize(self.weather_text[0])[0] + 5

            self.draw.text((day_hor, vert_loc[0]), self.weather_text[0], fill=(20, 142, 40), font=self.status_font)
            self.draw.text((fore_hor, vert_loc[0]), self.weather_text[1], fill=(20, 142, 40), font=self.status_font)
            self.draw.text((fore_hor, vert_loc[1]), self.weather_text[2], fill=(20, 142, 40), font=self.status_font)
            self.draw.text((fore_hor, vert_loc[2]), self.weather_text[3], fill=(20, 142, 40), font=self.status_font)

            # print(weather_text[0],  )
            # pop the first forecast and put it on the end to rotate through a new day each display.
            self.five_day_forecast.append(self.five_day_forecast.pop(0))

    # Pro-rata calculation of the RPM to turn fan at for the wind-speed.
    def set_fan_speed_from_wind_speed(self, wind_speed):

        if wind_speed <= min_wind_speed:
            logger.info("wind_speed <=3, set to 0")
            rpm = 0
        elif wind_speed >= max_wind_speed:
            rpm = self.fan_controller.fan_dict["max_rpm"]
        else:
            rpm = wind_speed/max_wind_speed * self.fan_controller.fan_dict["max_rpm"]

        logger.debug("Wind Speed of {} has RPM of {}".format(wind_speed, int(rpm)))

        self.fan_controller.rpm_queue.put_nowait(int(rpm))

    # Set the thermometer display by sending commands to the LED Strip.
    def set_thermometer_display(self, temperature):
        #calc pixels to illuminate
        pixels_to_display = int((temperature - self.min_temp) / (self.max_temp - self.min_temp) \
                            * self.thermo_pixel_count) + 1

        logger.debug("Number of pixels {}".format(pixels_to_display))

        pixels = []
        below_zero_pixels = 40
        above_zero_pixels = 49

        # for i in range(self.led_display.strip.numPixels()):
        # for i in range(below_zero_pixels + 1 + above_zero_pixels):
        for i in range(pixels_to_display):

            if i < below_zero_pixels:
                hue = float((below_zero_pixels - i)/below_zero_pixels) * 0.33 + 0.33
            else:
                #print("else")
                #hue = (49 - 41 + 40)/49 =
                #       49- 89 +40
                hue = float((above_zero_pixels - i + below_zero_pixels) / above_zero_pixels) * 0.10

            rgb = []

            if i== below_zero_pixels:
                rgb = (100, 100, 100)
            else:
                for j in range(3):
                    rgb.append(int(colorsys.hsv_to_rgb(hue, 0.75, 0.25)[j] *  255))

            # logger.debug("pixel {} hue{}, rgb{}".format(i,hue, rgb))

            colour = rpi_ws281x.Color(*rgb)
            pixels.append(colour)

        self.led_display.incoming_queue.put_nowait(pixels)

    # Displays date and time on the screen
    def display_time(self, time_to_display):
        date_str = time.strftime("%a %d %m", time_to_display)
        w, h = self.date_font.getsize(date_str)
        # print("date size", w, h)
        date_offset = int((self.disp.width - w)/2)  # Calculate offset to center text.
        self.draw.text((date_offset, 55), date_str, fill=(160, 160, 160), font=self.date_font)

        time_str = time.strftime("%H:%M", time_to_display)
        w, h = self.time_font.getsize(time_str)
        # print("time size", w, h)
        time_offset = int((self.disp.width - w)/2)  # Calculate offset to center text
        # logger.info(time_offset, date_offset)
        self.draw.text((time_offset, 15), time_str, fill=(255, 255, 255), font=self.time_font)

    # Writes the display frames to the display.
    def write_display(self):
        # display the frames
        im_r = self.image.rotate(0)  # set to 180 to flip
        self.disp.ShowImage(im_r)
        time.sleep(3)

    # Rotates the text - allows to write text portrait or whatever.
    def draw_text(self, position, font, text, image_red_or_black, rotation=0):
        w, h = font.getsize(text)
        mask = Image.new('1', (w, h), color=1)
        draw = ImageDraw.Draw(mask)
        draw.text((0, 0), text, 0, font)
        mask = mask.rotate(rotation, expand=True)
        image_red_or_black.paste(mask, position)

    # Main process of the thread.  Waits for the criteria to be reached for the displaying on the screen.
    def run(self):

        while True:
            if not self.time_queue.empty():
                time_to_display = self.time_queue.get_nowait()

                # Create blank image for drawing.
                self.image = Image.new("RGB", (self.disp.width, self.disp.height), "BLACK")
                self.draw = ImageDraw.Draw(self.image)

                # Drawing a circle around the outside.
                #self.draw.arc((1, 1, 239, 239), 0, 360, fill=(255, 0, 255))
                #self.draw.arc((2, 2, 238, 238), 0, 360, fill=(255, 0, 255))
                #self.draw.arc((3, 3, 237, 237), 0, 360, fill=(255, 0, 255))

                # Handle the Met Office Status - ie. the weather forecast
                self.handle_met_status()

                # Display time and date
                self.display_time(time_to_display)

                # Write to the display - should be ready.
                self.write_display()


                #logger.debug("LED On")
                #self.led_display.set_same_colour()
                #time.sleep(1)
                #logger.debug("LED Off")
                #self.led_display.pixel_clear()
                #time.sleep(1)

            time.sleep(1)


if __name__ == '__main__':
    clock_display = ClockDisplay()
    clock_display.start()

    while True:
        current_time = time.localtime()

        clock_display.time_queue.put_nowait(current_time)
        time.sleep(15)
