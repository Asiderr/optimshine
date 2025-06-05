#!/usr/bin/env python

import os
import requests

from logging import RootLogger
from optimshine.common_api import HEADERS

SHINE_API_URL = "https://shine-api.felicitysolar.com"
SHINE_API_ENDPOINTS = {
    "login": "/userlogin",
}


class ApiShine:
    def __init__(self, log: RootLogger):
        self.log = log

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
        response = requests.post(
            login_url,
            json=credentials,
            headers=HEADERS
        )

        if response.status_code != 200:
            self.log.error(
                f"Login attempt failed. Status code {response.status_code}"
            )
            return False

        login_response = response.json()

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
