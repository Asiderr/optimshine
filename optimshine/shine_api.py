#!/usr/bin/env python

import datetime
import os

from logging import RootLogger
from optimshine.common_api import CommonApi

SHINE_API_URL = "https://shine-api.felicitysolar.com"
SHINE_API_ENDPOINTS = {
    "login": "/userlogin",
    "production_data": "/storageRealtimeData/chart_storageRealtimeData_mate",
    "plant_list": "/plant/list_plant",
    "device_list": "/device/list_device_all_type"
}


class ApiShine(CommonApi):
    def __init__(self, log: RootLogger):
        self.log = log

    def _get_request_time(self):
        now = datetime.datetime.now()
        return now.strftime("%Y-%m-%d %H:%M:%S")

    def _get_shine_api_url(self, endpoint):
        if endpoint not in SHINE_API_ENDPOINTS.keys():
            self.log.error(f"{endpoint} API endpoint not found!")
            return None
        return f"{SHINE_API_URL}{SHINE_API_ENDPOINTS[endpoint]}"

    def login_shine(self):
        self.log.info("Trying to log in to felicitysolar shine API.")
        login_url = self._get_shine_api_url("login")
        shine_user = os.getenv("SHINE_USER")
        shine_password = os.getenv("SHINE_PASSWORD")

        if not shine_user or not shine_password:
            self.log.error("Shine API user or password not set! "
                           "Check '.env' file.")
            return False

        if not login_url:
            self.log.error("Parsing login API URL failed!")
            return False

        credentials = {
            "userName": shine_user,
            "password": shine_password,
            "lang": "en_US"
        }

        self.log.debug(f"Sending login request to {login_url}")
        login_response = self.api_post_request(login_url, credentials)
        if not login_response:
            self.log.error("Login attempt failed!")
            return False

        try:
            self.token = login_response["data"]["token"]
        except TypeError:
            self.log.error(
                f"Login attempt failed. {login_response['data']}"
            )
            return False

        if not self.token:
            self.log.error(
                "Login attempt failed. Login token not acquired."
            )
            return False
        else:
            self.log.info("Login attemp was successful.")
            return True

    def _get_plant_list(self):
        plant_url = self._get_shine_api_url("plant_list")
        plant_request = {
          "pageNum": 1,
          "pageSize": 10,
          "plantName": "",
          "deviceSn": "",
          "status": "",
          "isCollected": "",
          "plantType": "",
          "onGridType": "",
          "tagName": "",
          "realName": "",
          "orgCode": "",
          "authorized": "",
          "cityId": "",
          "countryId": "",
          "provinceId": ""
        }
        self.log.debug(f"Sending plant list request to {plant_url}")
        response = self.api_post_request(
            plant_url,
            plant_request,
            self.token
        )
        try:
            plants_data = response["data"]["dataList"]
        except TypeError:
            self.log.error(f"Getting plants list failed. {response['data']}")
            return False

        if not plants_data:
            self.log.error("No plants available!")
            return False

        self.plants_id = []
        for plant in plants_data:
            self.log.debug(f'ID - {plant["plantName"]}: {plant["id"]}')
            self.plants_id.append({plant["plantName"]: plant["id"]})

        self.log.info("Plant list successfully obtained.")
        return True

    def _get_device_list(self, plant_id, device_type):
        """
        INV, BP
        """
        device_list_url = self._get_shine_api_url("device_list")
        inverter_list_request = {
          "pageNum": 1,
          "pageSize": 10,
          "deviceType": device_type,
          "plantId": plant_id,
          "scope": 0
        }
        self.log.debug(f"Sending {device_type} list request to "
                       f"{device_list_url}")
        response = self.api_post_request(
            device_list_url,
            inverter_list_request,
            self.token
        )
        try:
            device_data = response["data"]["dataList"]
        except TypeError:
            self.log.error(f"Getting plants list failed. {response['data']}")
            return False

        if not device_data:
            self.log.error("No devices available!")
            return False

        device_list = []
        for device in device_data:
            self.log.debug(f'{device_type} Serial Number {device["deviceSn"]}')
            device_list.append(device["deviceSn"])

        self.log.info(f"{device_type} list successfully obtained.")
        return True
