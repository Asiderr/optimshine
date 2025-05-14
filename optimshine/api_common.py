#!/usr/bin/env python

import datetime
import requests

from logging import RootLogger

HEADERS = {
    "Content-Type": "application/json",
    "lang": "en_US",
    "User-Agent": "Mozilla/5.0"
}


class ApiCommon:
    def __init__(self, log: RootLogger):
        self.log = log

    def api_post_request(self, api_url, request, token=None):
        headers = HEADERS.copy()
        if token:
            headers.update({"Authorization": token})
        response = requests.post(
            api_url,
            json=request,
            headers=headers
        )

        if response.status_code != 200:
            self.log.error(
                f"API post failed. Status code {response.status_code}"
            )
            return None

        return response.json()

    def api_get_request(self, api_url):
        headers = HEADERS.copy()
        response = requests.get(
            api_url,
            headers=headers
        )

        if response.status_code != 200:
            self.log.error(
                f"API get failed. Status code {response.status_code}"
            )
            return None

        return response.json()

    def get_request_time(self, delta=None, future=False):
        if not delta:
            now = datetime.datetime.now()
        elif future:
            now = datetime.datetime.now() + delta
        else:
            now = datetime.datetime.now() - delta
        return now.strftime("%Y-%m-%d %H:%M:%S")
