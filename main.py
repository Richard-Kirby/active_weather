import time
import threading
import ntplib
import sys
import socket

import display
import met_weather_status


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
                    print("Synced @ {}" .format(i))
                    break

            except ntplib.NTPException:
                print("NTP Exception ", sys.exc_info())

            except socket.gaierror:
                print("socket.gaierror exception - can be a problem on first boot:", sys.exc_info())

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

            # checking whether display needs to be updated
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

            ''' 
            # If first starting up, signal via the semaphores.  Also write the time if it meets the regular update time.
            # Clear the screen first and then write date and time.
            if self.last_time_semaphore is None or (
                    current_time.tm_min % self.semaphore_interval_min == 0
                    and current_time.tm_min != self.last_time_semaphore):

                time_str = time.strftime("%Hh %Mm ", current_time)
                #print(time_str)

                self.semaphore_flagger.cmd_queue.put_nowait(time_str)

                self.last_time_semaphore = current_time.tm_min
            '''

            time.sleep(2)


if __name__ == "__main__":

    print("main program")

    active_weather_clock = ActiveWeatherClock(1)
    active_weather_clock.daemon = True
    active_weather_clock.start()

    while True:
        time.sleep(10)
