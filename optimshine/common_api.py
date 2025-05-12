#!/usr/bin/env python

import requests

from logging import RootLogger

HEADERS = {
    "Content-Type": "application/json",
    "lang": "en_US",
    "User-Agent": "Mozilla/5.0"
}


class CommonApi:
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
