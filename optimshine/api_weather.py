#!/usr/bin/env python

import datetime

from zoneinfo import ZoneInfo

from logging import RootLogger
from optimshine.api_common import ApiCommon


class ApiWeather(ApiCommon):
    def __init__(self, log: RootLogger):
        self.log = log

    def _get_timestamp_hour(self, date, time):
        dt_time = datetime.datetime.strptime(
            f"{date} {time}",
            "%Y-%m-%d %I:%M:%S %p",
        )
        hour = dt_time.replace(minute=0, second=0, microsecond=0,
                               tzinfo=ZoneInfo("UTC"))
        return int(hour.timestamp())

    def _get_solar_sunrise_sunset_time(self, latitude, longitude, date):
        sunrise_url = "https://api.sunrise-sunset.org/json?"
        sunrise_args = f"lat={latitude}&lng={longitude}&data={date}"

        self.log.debug("Sending sunrise/sunset request to"
                       f" {sunrise_url}{sunrise_args}")
        response = self.api_get_request(f"{sunrise_url}{sunrise_args}")
        if not response:
            self.log.error("Getting sunrise/sunset data failed!")
            return False
        try:
            self.sunrise = response["results"]["sunrise"]
            self.sunset = response["results"]["sunset"]
        except (TypeError, KeyError):
            self.log.error(f"Getting weather data failed. {response}")
            return False

        self.log.info("Sunrise/sunset time obtained successfully.")
        return True

    def get_weather_data(self, latitude, longitude, date):
        if not self._get_solar_sunrise_sunset_time(latitude, longitude,
                                                   date):
            self.log.error("Error during obtaining sunrise or sunset!")
            return False

        if not self.sunrise or not self.sunset:
            self.log.error("Sunrise or sunset cannot be none!")
            return False

        sunrise_hour_ts = self._get_timestamp_hour(date, self.sunrise)
        sunset_hour_ts = self._get_timestamp_hour(date, self.sunset)
        # Day ends after 12 AM
        if sunrise_hour_ts > sunset_hour_ts:
            sunset_hour_ts += 86400
        # First full hour after sunset
        sunset_hour_ts += 3600
        self.log.debug(f"Sunrise timestamp: {sunrise_hour_ts}")
        self.log.debug(f"Sunset timestamp: {sunset_hour_ts}")

        weather_ts = self._get_timestamp_hour(date, "12:00:00 AM")
        self.log.debug(f"Latitude: {latitude}")
        self.log.debug(f"Longitude: {longitude}")
        self.log.debug(f"Weather timestamp: {weather_ts}")

        weather_data_url = "https://devmgramapi.meteo.pl/meteorograms/um4_60"
        weather_data_request = {
            "date": weather_ts,
            "point": {
                "lat": latitude,
                "lon": longitude
            }
        }

        self.log.debug(f"Sending weather request to {weather_data_url}")
        response = self.api_post_request(
            weather_data_url,
            weather_data_request
        )
        if not response:
            self.log.error("Getting weather data failed!")
            return False
        try:
            first_sample_time = int(
                response["data"]["cldlow_aver"]["first_timestamp"]
            )
            self.log.debug(f"First timestamp: {first_sample_time}")
            interval = response["data"]["cldlow_aver"]["interval"]
            low_clouds_data = response["data"]["cldlow_aver"]["data"]
            samples_num = len(low_clouds_data)
        except (TypeError, KeyError):
            self.log.error(f"Getting weather data failed. {response}")
            return False

        if sunrise_hour_ts < first_sample_time:
            self.log.error("Wrong sunrise time!")
            return False

        if not low_clouds_data:
            self.log.error("No cloud data available!")
            return False

        # Polar night/Polar day
        if self.sunrise == self.sunset:
            self.weather_data = {
                "date": date,
                "first_sample_time": first_sample_time,
                "interval": interval,
                "low_clouds_data": low_clouds_data[:24],
                "sunrise_time": sunrise_hour_ts,
                "sunset_time": sunset_hour_ts,
            }
            self.log.info("Weather data obtained successfully")
            return True

        if not (sunrise_hour_ts % interval ==
                sunset_hour_ts % interval ==
                first_sample_time % interval == 0):
            self.log.error("Timestamps must be divisible by interval"
                           " otherwise sample numbers won't be correct")
            return False

        # Amount of hours from the beginning of the forecast
        first_sample = (sunrise_hour_ts - first_sample_time)/interval
        first_sample = int(first_sample)
        self.log.debug(f"First sample: {first_sample}")

        last_sample = (sunset_hour_ts - first_sample_time)/interval
        last_sample = int(last_sample)
        self.log.debug(f"Last sample: {last_sample}")

        samples_num = last_sample - first_sample
        striped_cloud_data = [
            low_clouds_data[i+first_sample] for i in range(0, samples_num)
        ]
        self.weather_data = {
                "date": date,
                "first_sample_time": sunrise_hour_ts,
                "interval": interval,
                "low_clouds_data": striped_cloud_data,
                "sunrise_time": sunrise_hour_ts,
                "sunset_time": sunset_hour_ts,
            }
        self.log.info("Weather data obtained successfully")
        return True
