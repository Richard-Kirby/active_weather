import time
import random
import threading
import queue

import logging
# create logger
logger = logging.getLogger(__name__)

import rpi_ws281x

# Gamma correction makes the colours perceived correctly.
gamma8 = [
    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,
    0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  0,  1,  1,  1,  1,
    1,  1,  1,  1,  1,  1,  1,  1,  1,  2,  2,  2,  2,  2,  2,  2,
    2,  3,  3,  3,  3,  3,  3,  3,  4,  4,  4,  4,  4,  5,  5,  5,
    5,  6,  6,  6,  6,  7,  7,  7,  7,  8,  8,  8,  9,  9,  9, 10,
   10, 10, 11, 11, 11, 12, 12, 13, 13, 13, 14, 14, 15, 15, 16, 16,
   17, 17, 18, 18, 19, 19, 20, 20, 21, 21, 22, 22, 23, 24, 24, 25,
   25, 26, 27, 27, 28, 29, 29, 30, 31, 32, 32, 33, 34, 35, 35, 36,
   37, 38, 39, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 50,
   51, 52, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64, 66, 67, 68,
   69, 70, 72, 73, 74, 75, 77, 78, 79, 81, 82, 83, 85, 86, 87, 89,
   90, 92, 93, 95, 96, 98, 99,101,102,104,105,107,109,110,112,114,
  115,117,119,120,122,124,126,127,129,131,133,135,137,138,140,142,
  144,146,148,150,152,154,156,158,160,162,164,167,169,171,173,175,
  177,180,182,184,186,189,191,193,196,198,200,203,205,208,210,213,
  215,218,220,223,225,228,231,233,236,239,241,244,247,249,252,255]


# Class to  control the LED Strip based on the tweets.
class LedStripControl(threading.Thread):

    # Set up the strip with the passed parameters.  The Gamma correction is done by the library, so it gete passed in.
    def __init__(self, led_count, led_pin):

        # Init the threading
        threading.Thread.__init__(self)

        self.strip = rpi_ws281x.PixelStrip(led_count, led_pin, gamma=gamma8)

        # Intialize the library (must be called once before other functions).
        self.strip.begin()
        self.incoming_queue = queue.Queue()

    def set_same_colour(self):
        for i in range(self.strip.numPixels()):
            self.strip.setPixelColor(i, rpi_ws281x.Color(55, 0, 0))
        self.strip.show()

    '''
    # Set the strip colours according to the passed in list.  Set Twinkle Ratio to 0 if you don't want any twinkle.
    def set_strip_colours(self, tweet_list, twinkle_ratio = 0.25, tweeter_filter = None):
        for pixel in range (0, len(tweet_list)):
            #print(colour_list[pixel])
            #print(pixel, tweet_list[pixel].name)

            twinkle_on_off = random.random()
            #print(twinkle_on_off)

            # If no filter, the show all pixels.
            if tweeter_filter is None:
                if float(twinkle_on_off) < float(twinkle_ratio):
                    self.strip.setPixelColor(pixel, rpi_ws281x.Color(0, 0, 0))
                else:
                    self.strip.setPixelColor(pixel, rpi_ws281x.Color(*tweet_list[pixel].colour))

            # Check against the filter
            elif tweet_list[pixel].id is tweeter_filter.id:
                self.strip.setPixelColor(pixel, rpi_ws281x.Color(*tweet_list[pixel].colour))

            # Otherwise set to off.
            else:
                self.strip.setPixelColor(pixel, rpi_ws281x.Color(0,0,0))


            #self.strip.setPixelColor(pixel, rpi_ws281x.Color(*tweet_list[pixel].colour))

        # The below commented out bit sets the rest to dark.
        for pixel in range(len(tweet_list), self.strip.numPixels()):
           self.strip.setPixelColor(pixel, rpi_ws281x.Color(0, 0, 0))

        self.strip.show()
    '''

    # Clears al the pixels.
    def pixel_clear(self):
        # Clear all the pixels
        for i in range(0, self.strip.numPixels()):  # Green Red Blue
            self.strip.setPixelColor(i, rpi_ws281x.Color(0, 0, 0))

        self.strip.show()

    def run(self):
        try:
            pixels =[]

            while True:
                # Get the latest commanded pixels from the queue
                while not self.incoming_queue.empty():
                    pixels = self.incoming_queue.get_nowait()
                    self.pixel_clear()

                logger.debug("LED Strip {}".format(len(pixels)))

                # Get number of pixels to display - max is number of pixels.
                pixels_to_display = min(len(pixels), self.strip.numPixels())

                logger.debug("Pixels to display {}".format(pixels_to_display))

                #self.set_same_colour()

                #time.sleep(3)

                # self.pixel_clear()

                for i in range(0, pixels_to_display):
                    # print(colour_list[pixel])
                    # logger.debug("{} {}".format(i, pixels[i]))
                    self.strip.setPixelColor(i, pixels[i])
                    self.strip.show()
                    time.sleep(0.1)

                    '''
                    twinkle_on_off = random.random()
                    # print(twinkle_on_off)

                    # If no filter, the show all pixels.
                    if tweeter_filter is None:
                        if float(twinkle_on_off) < float(twinkle_ratio):
                            self.strip.setPixelColor(pixel, rpi_ws281x.Color(0, 0, 0))
                        else:
                            self.strip.setPixelColor(pixeli, rpi_ws281x.Color(*tweet_list[pixel].colour))

                    # Check against the filter
                    elif tweet_list[pixel].id is tweeter_filter.id:
                        self.strip.setPixelColor(pixel, rpi_ws281x.Color(*tweet_list[pixel].colour))

                    # Otherwise set to off.
                    else:
                        self.strip.setPixelColor(pixel, rpi_ws281x.Color(0, 0, 0))

                    # self.strip.setPixelColor(pixel, rpi_ws281x.Color(*tweet_list[pixel].colour))
                '''
                # The below commented out bit sets the rest to dark.
                for i in range(pixels_to_display, self.strip.numPixels()):
                    self.strip.setPixelColor(i, rpi_ws281x.Color(0, 0, 0))
                    #logger.debug(i)

                self.strip.show()

                #logger.debug("strip showed")
                time.sleep(3)

        except KeyboardInterrupt:
            logger.exception("Keyboard interrupt")

        except:
            raise

        finally:
            # Todo: Can't get back to 0 RPM when shutdown by Ctrl-C
            logger.error("finally")

if __name__ == "__main__":

    # LED strip configuration:
    LED_COUNT      = 180      # Number of LED pixels.
    LED_PIN        = 18      # GPIO pin connected to the pixels (must support PWM!).
    LED_FREQ_HZ    = 800000  # LED signal frequency in hertz (usually 800khz)
    LED_DMA        = 10       # DMA channel to use for generating signal (try 5)
    LED_BRIGHTNESS = 255  # Set to 0 for darkest and 255 for brightest
    LED_INVERT     = False   # True to invert the signal (when using NPN transistor level shift)

    tweet_strip = LedStripControl(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA, LED_INVERT, LED_BRIGHTNESS)

    colours = [rpi_ws281x.Color(255,0,0) , rpi_ws281x.Color(255,0,0), rpi_ws281x.Color(255,255,0), rpi_ws281x.Color(0,255,0),
               rpi_ws281x.Color(0, 0, 255)]

    while True:
        tweet_strip.pixel_clear()

        time.sleep(1)

        #tweet_strip.set_strip_colours(colours)
        tweet_strip.set_same_colour()
        time.sleep(1)