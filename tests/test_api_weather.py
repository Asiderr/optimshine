import io
import logging
import unittest

import optimshine.api_weather as api

from unittest.mock import patch
import optimshine.optim_config as config


class TestPseApi(unittest.TestCase):
    def setUp(self):
        cls_optim_config = config.OptimConfig()
        cls_optim_config.logger_setup()
        self.log = cls_optim_config.log
        cls_optim_config.envs_setup("tests/.testenv")

    def tearDown(self):
        self.log.handlers.clear()

    def test_get_timestamp_hour(self):
        cls_api_weather = api.ApiWeather(self.log)
        timestamp = cls_api_weather._get_timestamp_hour("2025-04-14",
                                                        "2:29:54 AM")

        self.assertEqual(timestamp, 1744596000)


if __name__ == "__main__":
    unittest.main()
