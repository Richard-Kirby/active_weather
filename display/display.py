#!/usr/bin/python
# -*- coding: UTF-8 -*-
#import chardet
import os
import sys 
import time

import spidev as SPI
from .lib import LCD_1inch28 # Using the round 240 x 240 pixel Waveshare round display
from PIL import Image, ImageDraw, ImageFont
from .fan_control import FanController

import time
import threading
import queue

import logging
# create logger
logger = logging.getLogger(__name__)


# Raspberry Pi pin configuration:
RST = 27
DC = 25
BL = 18
bus = 0 
device = 0 

icon_dict = {
    "Clear" :   {"icon":'./display/icons/Sunny.png', "mist": 0},
    "Sunny" :   {"icon":'./display/icons/Sunny.png', "mist": 0},
    "PrtCld":   {"icon":'./display/icons/PrtCld.png',"mist": 0},
    "PrtCLd":   {"icon":'./display/icons/PrtCld.png', "mist": 0},
    "Not used": {"icon":'./display/icons/weather_vane.png',"mist": 0},
    "Mist":     {"icon":'./display/icons/weather_vane.png',"mist": 0},
    "Fog":      {"icon":'./display/icons/weather_vane.png',"mist": 0},
    "Cloudy":   {"icon":'./display/icons/Cloudy.png',"mist": 0},
    "Overcst":  {"icon":'./display/icons/Overcst.png',"mist": 0},
    "L rain":   {"icon":'./display/icons/L_rain.png', "mist": 0}, # "Light rain shower (night)",
    "L shwr":   {"icon":'./display/icons/L_shwr.png', "mist": 0},  # Light rain shower (day)",
    "Drizzl":   {"icon":'./display/icons/weather_vane.png',"mist": 0},
    "L rain":   {"icon":'./display/icons/L_rain.png', "mist": 0}, # "Light rain",
    "Hvy sh":   {"icon":'./display/icons/H_rain.png', "mist": 0}, # "Heavy rain shower (night)",
    "Hvy sh":   {"icon":'./display/icons/H_rain.png', "mist": 0}, # "Heavy rain shower (day)",
    "H rain":   {"icon":'./display/icons/H_rain.png', "mist": 0},
    "Slt sh":   {"icon":'./display/icons/weather_vane.png', "mist": 0}, # "Sleet shower (night)",
    "Slt sh":   {"icon":'./display/icons/weather_vane.png', "mist": 0},# "Sleet shower (day)",
    "Sleet":    {"icon":'./display/icons/weather_vane.png', "mist": 0},
    "Hail sh":  {"icon":'./display/icons/weather_vane.png', "mist": 0}, # Hail shower (night)",
    "Hail sh":  {"icon":'./display/icons/weather_vane.png', "mist": 0},  # "Hail shower (day)",
    "Hail":     {"icon": './display/icons/weather_vane.png', "mist": 0},
    "L snw sh": {"icon": './display/icons/weather_vane.png', "mist": 0}, # "Light snow shower (night)",
    "L snw sh": {"icon": './display/icons/weather_vane.png', "mist": 0}, # "Light snow shower (day)",
    "L snw":    {"icon": './display/icons/weather_vane.png', "mist": 0},
    "H snw sh": {"icon": './display/icons/weather_vane.png', "mist": 0}, # "Heavy snow shower (night)",
    "H snw sh": {"icon": './display/icons/weather_vane.png', "mist": 0},  # "Heavy snow shower (day)",
    "H snw":    {"icon": './display/icons/weather_vane.png', "mist": 0},
    "Thndr sh": {"icon": './display/icons/weather_vane.png',"mist": 0},  # "Thunder shower (night)",
    "Thndr sh": {"icon": './display/icons/weather_vane.png',"mist": 0},  # "Thunder shower (day)",
    "Thndr":    {"icon": './display/icons/weather_vane.png', "mist": 0}
}


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

        if wind_speed < 3:
            logger.info("wind_speed <3, set to 0")
            rpm = 0
        elif wind_speed > 45:
            rpm = self.fan_controller.fan_dict["max_rpm"]
        else:
            rpm = wind_speed/45 * (self.fan_controller.fan_dict["max_rpm"] - self.fan_controller.fan_dict["min_rpm"]) \
                  + self.fan_controller.fan_dict["min_rpm"]

        logger.debug("Wind Speed of {} has RPM of {}".format(wind_speed, int(rpm)))

        self.fan_controller.rpm_queue.put_nowait(int(rpm))

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

            time.sleep(1)


if __name__ == '__main__':
    clock_display = ClockDisplay()
    clock_display.start()

    while True:
        current_time = time.localtime()

        clock_display.time_queue.put_nowait(current_time)
        time.sleep(15)
