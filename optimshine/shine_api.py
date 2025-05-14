#!/usr/bin/env python

import datetime
import os
import time

from logging import RootLogger
from optimshine.common_api import CommonApi

SHINE_API_URL = "https://shine-api.felicitysolar.com"
SHINE_API_ENDPOINTS = {
    "login": "/userlogin",
    "plant_list": "/plant/list_plant",
    "device_list": "/device/list_device_all_type",
    "production_data": "/storageRealtimeData/chart_storageRealtimeData_mate",
    "device_values": "/device/get_device_snapshot",
    "setting_values": "/deviceCommand/get_command_setting_original_value",
    "setting_command": "/deviceCommand/create_setting_command",
    "command_status": "/deviceCommand/get_device_command_status",
}
SHINE_PV_DATA_LABELS = {
    "pvTotalPower": "PV power generated",
    "acTtlInpower": "Grid power",
    "acTotalOutActPower": "Total load",
    "emsPower": "Battery Power",
}
SHINE_DEVICE_VALUES = {
    "battery_soc": "emsSoc"
}
SHINE_SETTING_VALUES = {
    "battery_charge_current": "bmchc",
    "battery_discharge_current": "bmdcu",
}


class ApiShine(CommonApi):
    def __init__(self, log: RootLogger):
        self.log = log

    def _get_request_time(self, delta=None):
        if not delta:
            now = datetime.datetime.now()
        else:
            now = datetime.datetime.now() - delta
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
                f"Login attempt failed. {login_response}"
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
        if not hasattr(self, "token"):
            self.log.error("Session is not authorized!")
            return False

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
        if not response:
            self.log.error("Getting plant list failed!")
            return False

        try:
            plants_data = response["data"]["dataList"]
        except TypeError:
            self.log.error(f"Getting plants list failed. {response}")
            return False

        if not plants_data:
            self.log.error("No plants available!")
            return False

        self.plants_id = {}
        for plant in plants_data:
            self.log.debug(f'ID - {plant["plantName"]}: {plant["id"]}')
            self.plants_id.update({plant["plantName"]: plant["id"]})

        self.log.info("Plant list successfully obtained.")
        return True

    def _get_device_list(self, plant_id, device_type):
        """
        INV, BP
        """
        if not hasattr(self, "token"):
            self.log.error("Session is not authorized!")
            return False

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
        if not response:
            self.log.error("Getting device list failed!")
            return False
        try:
            device_data = response["data"]["dataList"]
        except TypeError:
            self.log.error(f"Getting device list failed. {response}")
            return False

        if not device_data:
            self.log.error("No devices available!")
            return False

        self.device_list = []
        for device in device_data:
            self.log.debug(f'{device_type} Serial Number {device["deviceSn"]}')
            self.device_list.append(device["deviceSn"])

        self.log.info(f"{device_type} list successfully obtained.")
        return True

    def _get_pv_production_data(self, inverter_serial_number, data_date=None):
        if not hasattr(self, "token"):
            self.log.error("Session is not authorized!")
            return False

        if not data_date:
            data_date = self._get_request_time(datetime.timedelta(days=1))

        production_data_url = self._get_shine_api_url("production_data")
        get_data_request = {
          "deviceSn": inverter_serial_number,
          "chartScope": 0,
          "chartDrawingType": 0,
          "chartType": 1,
          "chartScopeType": 0,
          "timeDimension": "hour",
          "dateStr": data_date,
          "field": [
                "pvTotalPower",        # Produced PV energy
                "acTtlInpower",        # Grid Energy
                "acTotalOutActPower",  # Home Load
                "emsPower",            # Battery Power
          ]
        }

        self.log.debug(f"Sending data request to {production_data_url}")
        response = self.api_post_request(
            production_data_url,
            get_data_request,
            self.token
        )
        if not response:
            self.log.error("Getting PV data failed!")
            return False

        try:
            pv_data = response["data"]["storageMateDTOS"]
            pv_data_time = response["data"]["dataTime"]
        except TypeError:
            self.log.error(f"Getting PV data failed. {response}")
            return False

        if not pv_data or not pv_data_time:
            self.log.error("No PV data acquired!")
            return False

        self.pv_data = {
            "inverter_sn": inverter_serial_number,
            "data_date": data_date,
            "data_time": pv_data_time,
            "data": {}
        }
        for param in pv_data:
            param_data = {
                param["field"]: {
                    "label": SHINE_PV_DATA_LABELS[param["field"]],
                    "data": param["data"],
                    "unit": param["unit"],
                },
            }
            self.pv_data["data"].update(param_data)

        self.log.info("PV production data successfully obtained.")
        return True

    def _get_setting_value(self, inverter_serial_number, value_name):
        if not hasattr(self, "token"):
            self.log.error("Session is not authorized!")
            return False

        try:
            value_alias = SHINE_SETTING_VALUES[value_name]
        except KeyError:
            self.log.error(f"{value_name} is not supported!")
            return False

        settings_url = self._get_shine_api_url("setting_values")
        get_settings_request = {
            "deviceSn": inverter_serial_number,
            "oldVersion": 1
        }

        self.log.debug(f"Sending setting values request to {settings_url}")
        response = self.api_post_request(
            settings_url,
            get_settings_request,
            self.token
        )
        if not response:
            self.log.error("Getting setting values failed!")
            return False
        try:
            self.setting_value = (
                response["data"][value_alias]
            )
        except TypeError:
            self.log.error(f"Getting {value_name} value failed."
                           f" {response}")
            return False

        self.log.info(f"{value_name} value successfully obtained.")
        return True

    def _get_device_value(self, inverter_serial_number, value_name):
        if not hasattr(self, "token"):
            self.log.error("Session is not authorized!")
            return False

        try:
            value_alias = SHINE_DEVICE_VALUES[value_name]
        except KeyError:
            self.log.error(f"{value_name} is not supported!")
            return False

        device_url = self._get_shine_api_url("device_values")
        get_device_request = {
            "deviceSn": inverter_serial_number,
            "deviceType": "OC",
            "dateStr": self._get_request_time(),
        }

        self.log.debug(f"Sending device values request to {device_url}")
        response = self.api_post_request(
            device_url,
            get_device_request,
            self.token
        )
        if not response:
            self.log.error("Getting device values failed!")
            return False
        try:
            self.device_value = (
                response["data"][value_alias]
            )
        except TypeError:
            self.log.error(f"Getting {value_name} value failed."
                           f" {response}")
            return False

        self.log.info(f"{value_name} value successfully obtained.")
        return True

    def _setting_command_status(self, id, timeout=10):
        if not hasattr(self, "token"):
            self.log.error("Session is not authorized!")
            return False

        command_status_url = self._get_shine_api_url("command_status")
        command_status_request = {"id": id}
        self.log.debug("Sending setting command request to"
                       f" {command_status_url}")

        for _ in range(0, timeout, 2):
            response = self.api_post_request(
                command_status_url,
                command_status_request,
                self.token
            )
            if not response:
                self.log.error("Getting command stasus failed!")
                return False
            try:
                command_status = response["data"]["result"]
            except TypeError:
                self.log.error(f"Checking command status failed."
                               f" {response}")
                return False
            if command_status == 1:
                self.log.info("Setting command sent successfuly.")
                return True
            else:
                time.sleep(2)
        self.log.error("Command timeout!")
        return False

    def set_charge_current(self, inverter_serial_number, current):
        if not hasattr(self, "token"):
            self.log.error("Session is not authorized!")
            return False

        current_formated = str(10*current)
        timestamp_ms = int(datetime.datetime.now().timestamp() * 1000)
        settings_url = self._get_shine_api_url("setting_command")

        charge_current_request = {
            "deviceSn": inverter_serial_number,
            "timeZone": "Europe/Warsaw",
            "timestamp": timestamp_ms,
            "oldVersion": 1,
            "useType": 5,
            "groupId": 1,
            "deviceCommands": [
                {
                    "dataHandlerType": 0,
                    "fieldName": "bmchc",
                    "groupId": 0,
                    "paramType": 0,
                    "useType": 3,
                    "fieldValue": current_formated
                }
            ],
            "realContentParam": [
                "bmchc"
            ]
        }

        self.log.debug(f"Sending setting command request to {settings_url}")
        response = self.api_post_request(
            settings_url,
            charge_current_request,
            self.token
        )
        if not response:
            self.log.error(response)
            self.log.error("Setting charge current failed!")
            return False
        try:
            command_id = response["data"][0]["id"]
        except TypeError:
            self.log.error(f"Sending setting command failed."
                           f" {response}")
            return False

        self.log.debug("Checking command status.")
        status = self._setting_command_status(command_id)
        if not status:
            self.log.error("Wrong command status."
                           " Setting charge current failed!")
            return False
        self.log.info("Charge current successfuly set.")
        return True
