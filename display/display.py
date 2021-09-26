#!/usr/bin/python
# -*- coding: UTF-8 -*-
#import chardet
import os
import sys 
import time
import logging
import spidev as SPI
#sys.path.append("..")
from lib import LCD_1inch28 # Using the round 240 x 240 pixel Waveshare round display
from PIL import Image, ImageDraw, ImageFont

import time
import threading
import queue

# Raspberry Pi pin configuration:
RST = 27
DC = 25
BL = 18
bus = 0 
device = 0 
logging.basicConfig(level=logging.DEBUG)


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


        logging.info("icon and then draw circle")

        main_font = './display/HammersmithOne-Regular.ttf'

        self.date_font = ImageFont.truetype(main_font, 25)
        self.time_font = ImageFont.truetype(main_font, 30)
        self.location_font = ImageFont.truetype(main_font, 30)
        self.status_font = ImageFont.truetype(main_font, 30)

        # Queue to receive time updates.
        self.time_queue = queue.Queue()

        # Queue and Variable for Met Office 5 day forecast
        self.weather_text = ""
        self.met_forecast_queue = queue.Queue()
        self.five_day_forecast = None

    def handle_met_status(self):

        weather_icon = Image.open('./display/icons/sunny_weather_icon.png')
        self.image.paste(weather_icon, (56, 56))
        self.draw = ImageDraw.Draw(self.image)


        if not self.met_forecast_queue.empty():
            while not self.met_forecast_queue.empty():
                self.five_day_forecast = self.met_forecast_queue.get_nowait()

        if self.five_day_forecast is not None and len(self.five_day_forecast) == 5:
            degree_sign = u"\N{DEGREE SIGN}"

            self.weather_text = [self.five_day_forecast[0]['date'][:3],"{} {}{}C {}%".format(
                                self.five_day_forecast[0]['day_weather_type'],
                                self.five_day_forecast[0]['high_temp'], degree_sign,
                                self.five_day_forecast[0]['prob_ppt_day']),

                            "{} {}{}C {}%".format(
                                self.five_day_forecast[0]['night_weather_type'],
                                self.five_day_forecast[0]['low_temp'], degree_sign,
                                self.five_day_forecast[0]['prob_ppt_night'])]

        # Weather Text drawn here.
        if len(self.weather_text) > 0:

            fc_size = []

            for i in range(3):
                fc_size.append(self.status_font.getsize(self.weather_text[i]))  # width, height size

            day_hor = 0
            day_vert = 265  # vertical location of day string - adjust forecast by their height

            vert_loc = [day_vert, day_vert - (fc_size[1][1] - fc_size[0][1]),
                        day_vert - (fc_size[2][1] - fc_size[0][1]) - 35]

            fore_hor = day_hor + fc_size[0][0] + 5

            self.draw_text((vert_loc[0], day_hor), self.status_font, self.weather_text[0],
                           self.image_black, rotation=270)
            self.draw_text((vert_loc[1], fore_hor),
                           self.status_font, self.weather_text[1], self.image_black, rotation=270)
            self.draw_text((vert_loc[2], fore_hor),
                           self.status_font, self.weather_text[2], self.image_black, rotation=270)

            # print(weather_text[0],  )
            # pop the first forecast and put it on the end to rotate through a new day each display.
            self.five_day_forecast.append(self.five_day_forecast.pop(0))

    # Displays date and time on the screen
    def display_time(self, time_to_display):
        date_str = time.strftime("%a %d %m %Y", time_to_display)
        w, h = self.date_font.getsize(date_str)
        # print("date size", w, h)
        date_offset = int((self.disp.width - w)/2)  # Calculate offset to center text.
        self.draw.text((date_offset, 50), date_str, fill=(128, 255, 128), font=self.date_font)

        time_str = time.strftime("%H:%M", time_to_display)
        w, h = self.time_font.getsize(time_str)
        # print("time size", w, h)
        time_offset = int((self.disp.width - w)/2)  # Calculate offset to center text
        print(time_offset, date_offset)
        self.draw.text((time_offset, 200), time_str, fill=(128, 0, 128), font=self.date_font)

    # Writes the display frames to the display.
    def write_display(self):
        # display the frames
        im_r = self.image.rotate(180)
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

                self.draw.arc((1, 1, 239, 239), 0, 360, fill=(255, 0, 255))
                self.draw.arc((2, 2, 238, 238), 0, 360, fill=(255, 0, 255))
                self.draw.arc((3, 3, 237, 237), 0, 360, fill=(255, 0, 255))

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
