import time
import threading
import ntplib
import sys
import socket
import logging
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

# Project packages
import display
import met_weather_status

'''

logging.config.
fh = logging.FileHandler('logger.log')
fh.setLevel(logging.DEBUG)
# create console handler with a higher log level
ch = logging.StreamHandler()
ch.setLevel(logging.ERROR)
# create formatter and add it to the handlers
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)
ch.setFormatter(formatter)
# add the handlers to the logger
logger.addHandler(fh)
logger.addHandler(ch)
'''


# Main class for the Active Weather Clock.  Relies on several other packages to implement.
class ActiveWeatherClock(threading.Thread):

    def __init__(self, display_interval_min):

        # Init the threading
        threading.Thread.__init__(self)

        # Start the display
        self.clock_display = display.ClockDisplay()
        self.clock_display.start()

        self.last_time_displayed = None
        self.display_interval_min = display_interval_min

        # check on the time sync.  If not synched yet, then wait and break out of the loop when detected or max loop
        # reached
        ntp_client = ntplib.NTPClient()

        # Give some maximum time to sync, otherwise crack on.
        for i in range (90):
            try:
                ntp_response = ntp_client.request('europe.pool.ntp.org', version=4)
                # print (ntp_response.offset)

                if ntp_response.offset < 2:
                    logger.debug("Synced @ {}" .format(i))
                    break

            except ntplib.NTPException:
                logger.error("NTP Exception ", sys.exc_info())

            except socket.gaierror:
                logger.error("socket.gaierror exception - can be a problem on first boot:", sys.exc_info())

            time.sleep(1)

        # Met Status - Start up the thread that deals with the Met Status.
        self.met_status_thread = met_weather_status.MetWeatherStatus()
        self.last_forecast = None
        self.forecast_interval_min = 10
        self.met_status_thread.daemon = True
        self.met_status_thread.start()

    # Main method that runs regularly in the thread.
    def run(self):

        while True:
            current_time = time.localtime()

            # checking if time display needs to be updated
            if self.last_time_displayed is None or (
                    current_time.tm_min % self.display_interval_min == 0
                    and current_time.tm_min != self.last_time_displayed):

                self.clock_display.time_queue.put_nowait(current_time)
                self.last_time_displayed = current_time.tm_min

            # checking if weather display needs to be updated
            if len(self.met_status_thread.five_day_forecast) == 5 and \
                    (self.last_forecast is None or (current_time.tm_min % self.forecast_interval_min == 0
                                                    and current_time.tm_min != self.last_forecast)):
                self.clock_display.met_forecast_queue.put_nowait(self.met_status_thread.five_day_forecast)
                self.last_forecast = current_time.tm_min  # stays at None until a valid forecast sent

            time.sleep(2)


if __name__ == "__main__":

    logger.debug("main program")

    active_weather_clock = ActiveWeatherClock(1)
    active_weather_clock.daemon = True
    active_weather_clock.start()

    while True:
        time.sleep(10)
