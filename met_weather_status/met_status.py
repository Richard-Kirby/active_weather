import requests
import json
import threading
import time
from datetime import date
import sys

weather_types =[ # comments are original Met Office text
    "Clear",    # Clear Night
    "Sunny",    # Sunny day
    "PrtCld",  # "Partly cloudy (night)",
    "PrtCLd",  # "Partly cloudy (day)",
    "Not used",
    "Mist",
    "Fog",
    "Cloudy",
    "Overcs",
    "L rain",  # "Light rain shower (night)",
    "L shwr",  # Light rain shower (day)",
    "Drizzl",
    "L rain",  # "Light rain",
    "Hvy sh",  # "Heavy rain shower (night)",
    "Hvy sh",  # "Heavy rain shower (day)",
    "H rain",
    "Slt sh",  # "Sleet shower (night)",
    "Slt sh",  # "Sleet shower (day)",
    "Sleet",
    "Hail sh",  # Hail shower (night)",
    "Hail sh",  # "Hail shower (day)",
    "Hail",
    "L snw sh",  # "Light snow shower (night)",
    "L snw sh",  # "Light snow shower (day)",
    "L snw",
    "H snw sh",  # "Heavy snow shower (night)",
    "H snw sh",  # "Heavy snow shower (day)",
    "H snw",
    "Thndr sh",  # "Thunder shower (night)",
    "Thndr sh",  # "Thunder shower (day)",
    "Thndr"]


# Class that manages the TFL status - sorts out the credentials and makes the queries when asked.
class MetWeatherStatus(threading.Thread):

    # Get setup, including reading in credentials from the JSON file.  Credentials need to be obtained from TFL.
    def __init__(self):
        # Init the threading
        threading.Thread.__init__(self)

        # Grab the credentials.  TODO: everyone has to get their own credentials.  Not in the repo.
        with open('met_weather_status/met_credentials.secret') as json_data_file:
            config = json.load(json_data_file)

        # assign to appropriate variables - get used for each call to get status.
        self.application_key = config['credentials']['application_key']

        self.status_request_url = "http://datapoint.metoffice.gov.uk/public/data/val/wxfcs/all/json/324151?res=daily&key={}"\
            .format(self.application_key)

        self.status_dictionary = None

        self.five_day_forecast = []

        # print(self.status_request_url)

    # Get the status from the TFL site and process it to get just the summary status.
    def get_summary_status(self):

        ret_five_day_forecast = []

        try:
            # print("trying")

            raw_data = requests.get(self.status_request_url)
            #print(raw_data)

            try:
                result = raw_data.json()
                # Process each day in turn.  The Met Office data is nested - this gets us to the forecasts.
                for day in result["SiteRep"]["DV"]["Location"]["Period"]:
                    # put into date object - Met Office gives in format of YYYY-MM-DDZ - not sure what the Z is for.
                    forecast_date = date(int(day["value"][:4]), int(day["value"][5:7]), int(day["value"][8:10]))

                    # Met Office provides day forecast first, followed by night.  Night is from sundown previous day
                    # to sunrise.  Day from Sunrise to Sunset.
                    day_forecast = day["Rep"].pop(0)
                    night_forecast = day["Rep"].pop(0)

                    # print(int(day_forecast["W"]))
                    # Create a dictionary for each day.
                    simple_day_forecast = {"date": forecast_date.strftime("%a %d %m %y"),
                                           "day_weather_type": weather_types[int(day_forecast["W"])],
                                           "night_weather_type": weather_types[int(night_forecast["W"])],
                                           "high_temp": day_forecast["Dm"],
                                           "low_temp": night_forecast["Nm"],
                                           "prob_ppt_day": day_forecast["PPd"],
                                           "prob_ppt_night": night_forecast["PPn"]}

                    ret_five_day_forecast.append(simple_day_forecast)

            except:
                print("Problem with dealing with {} from Met Office".format(raw_data))
                raise

        except:
            print("Met Get status get failed - random number generator or Internet not avail?")
            error = sys.exc_info()
            print("*** Error in Met Status: {}".format(error))

        return ret_five_day_forecast

    def run(self):
        # trying to ensure there is enough entropy to get started.  Just wait for 5 min.  Could be more clever.

        # Get the status every once in a while
        while True:
            self.five_day_forecast = self.get_summary_status()
            time.sleep(120)


if __name__ == "__main__":
    met_weather_status = MetWeatherStatus()
    met_weather_status.start()

