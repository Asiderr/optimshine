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

    def _get_solar_sunrise_sunset_time(self, latitiude, longtitude, date):
        sunrise_url = "https://api.sunrise-sunset.org/json?"
        sunrise_args = f"lat={latitiude}&lng={longtitude}&data={date}"

        self.log.debug("Sending sunrise/sunset request to"
                       f" {sunrise_url}{sunrise_args}")
        response = self.api_get_request(f"{sunrise_url}{sunrise_args}")
        if not response:
            self.log.error("Getting sunrise/sunset data failed!")
            return False
        try:
            self.sunrise = response["result"]["sunrise"]
            self.sunset = response["result"]["sunset"]
        except TypeError:
            self.log.error(f"Getting weather data failed. {response}")
            return False

        self.log.info("Sunrise/sunset time obtained successfully.")
        return True

    def get_weather_data(self, latitiude, longtitude, date):
        self._get_solar_sunrise_sunset_time(latitiude, longtitude, date)
        if not self.sunrise or not self.sunset:
            self.log.error("Getting sunrise or sunset time failed")
            return False

        sunrise_hour_ts = self._get_timestamp_hour(date, self.sunrise)
        sunset_hour_ts = self._get_timestamp_hour(date, self.sunset)
        weather_ts = self._get_timestamp_hour(date, "12:00:00 AM")
        weather_data_url = "https://devmgramapi.meteo.pl/meteorograms/um4_60"
        weather_data_request = {
            "date": weather_ts,
            "point": {
                "lat": latitiude,
                "lon": longtitude
            }
        }

        self.log.debug(f"Sending weather request to {weather_data_url}")
        response = self.api_post_request(
            weather_data_url,
            weather_data_request
        )
        if not response:
            self.log.error("Getting device list failed!")
            return False
        try:
            first_sample_time = int(
                response["cldlow_aver"]["first_timestamp"]
            ),
            interval = response["cldlow_aver"]["interval"],
            low_clouds_data = response["cldlow_aver"]["data"]
            samples_num = len(low_clouds_data)
        except TypeError:
            self.log.error(f"Getting weather data failed. {response}")
            return False

        if sunrise_hour_ts < first_sample_time:
            self.log.error("Wrong sunrise time!")
            return False

        if not low_clouds_data:
            self.log.error("No cloud data available!")
            return False

        # Polar night/Polar day
        if sunrise_hour_ts == sunset_hour_ts:
            self.weather_data = {
                "date": date,
                "first_sample_time": first_sample_time,
                "interval": interval,
                "low_clouds_data": low_clouds_data,
            }
            self.log.info("Weather data obtained successfully")
            return True

        first_sample = (sunrise_hour_ts - first_sample_time)/interval

        # Day ends after 12 AM
        if sunrise_hour_ts > sunset_hour_ts:
            samples_num -= first_sample
            striped_cloud_data = [
                low_clouds_data[i+first_sample] for i in range(0, samples_num)
            ]
            self.weather_data = {
                "date": date,
                "first_sample_time": sunrise_hour_ts,
                "interval": interval,
                "low_clouds_data": striped_cloud_data,
            }
            self.log.info("Weather data obtained successfully")
            return True

        # Day ends before 12 AM
        last_sample = (sunset_hour_ts - first_sample_time)/interval
        samples_num = last_sample - first_sample
        striped_cloud_data = [
            low_clouds_data[i+first_sample] for i in range(0, samples_num)
        ]
        self.weather_data = {
                "date": date,
                "first_sample_time": sunrise_hour_ts,
                "interval": interval,
                "low_clouds_data": striped_cloud_data,
            }
        self.log.info("Weather data obtained successfully")
        return True
