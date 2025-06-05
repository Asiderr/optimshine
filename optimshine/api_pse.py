#!/usr/bin/env python

from logging import RootLogger
from optimshine.api_common import ApiCommon


class ApiPse(ApiCommon):
    """
    ApiPse is a class for interacting with the PSE RCE API.
    """
    def __init__(self, log: RootLogger):
        self.log = log

    def get_pse_data(self, date):
        """
        Retrieves PSE RCE data for a specified date.

        Args:
            date (str): The business date for which to retrieve RCE
                        data in 'YYYY-MM-DD' format.

        Returns:
            bool: True if data retrieval is successful, False otherwise.
        """
        self.log.info(f"Getting PSE RCE data for {date}.")
        pse_url = (
            "https://api.raporty.pse.pl/api/rce-pln?$filter="
            f"business_date%20eq%20%27{date}%27"
        )

        response = self.api_get_request(pse_url)
        if not response:
            self.log.error("Getting PSE data failed!")
            return False

        try:
            response_data = response["value"]
        except (TypeError, KeyError):
            self.log.error(f"Getting RCE values failed! {response}")
            return False

        if not response_data:
            self.log.error("No RCE values available!")
            return False

        self.rce_date = date
        self.rce_prices = {}
        for quarter in response_data:
            self.rce_prices.update({quarter["udtczas"]: quarter["rce_pln"]})

        self.log.info(f"Successfully obtained RCE data for {self.rce_date}.")
        return True
