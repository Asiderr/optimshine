#!/usr/bin/env python
#
# Copyright 2025 Norbert Kamiński <norbert.kaminski@xarium.world>
#
# SPDX-License-Identifier: LGPL-3.0-or-later
#

import io
import logging
import unittest

import optimshine.api_pse as api

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

    @patch("optimshine.api_common.ApiCommon.api_get_request")
    def test_get_pse_data_none_response(self, mock_api_get_request):
        stdio = io.StringIO()
        mock_api_get_request.return_value = None

        handler = logging.StreamHandler(stream=stdio)
        self.log.addHandler(handler)
        cls_api_pse = api.ApiPse(self.log)
        status = cls_api_pse.get_pse_data("2025-04-14")
        stdout = stdio.getvalue()

        self.assertFalse(status)
        self.assertIn("Getting PSE data failed!", stdout)

    @patch("optimshine.api_common.ApiCommon.api_get_request")
    def test_get_pse_data_wrong_response(self, mock_api_get_request):
        stdio = io.StringIO()
        mock_api_get_request.return_value = {"data": "Test issue"}

        handler = logging.StreamHandler(stream=stdio)
        self.log.addHandler(handler)
        cls_api_pse = api.ApiPse(self.log)
        status = cls_api_pse.get_pse_data("2025-04-14")
        stdout = stdio.getvalue()

        self.assertFalse(status)
        self.assertIn("Getting RCE values failed! {'data': 'Test issue'}",
                      stdout)

    @patch("optimshine.api_common.ApiCommon.api_get_request")
    def test_get_pse_data_empty_data(self, mock_api_get_request):
        stdio = io.StringIO()
        mock_api_get_request.return_value = {"value": []}

        handler = logging.StreamHandler(stream=stdio)
        self.log.addHandler(handler)
        cls_api_pse = api.ApiPse(self.log)
        status = cls_api_pse.get_pse_data("2025-04-14")
        stdout = stdio.getvalue()

        self.assertFalse(status)
        self.assertIn("No RCE values available!", stdout)

    @patch("optimshine.api_common.ApiCommon.api_get_request")
    def test_get_pse_data_pass(self, mock_api_get_request):
        mock_api_get_request.return_value = {
            "value": [
                {
                  "doba": "2025-05-14",
                  "rce_pln": 439.58,
                  "udtczas": "2025-05-14 00:15:00",
                  "udtczas_oreb": "00:00 - 00:15",
                  "business_date": "2025-05-14",
                  "source_datetime": "2025-05-13 13:49:22.204"
                },
                {
                  "doba": "2025-05-14",
                  "rce_pln": 449.58,
                  "udtczas": "2025-05-14 00:30:00",
                  "udtczas_oreb": "00:15 - 00:30",
                  "business_date": "2025-05-14",
                  "source_datetime": "2025-05-13 13:49:22.204"
                },
                {
                  "doba": "2025-05-14",
                  "rce_pln": 459.58,
                  "udtczas": "2025-05-14 00:45:00",
                  "udtczas_oreb": "00:30 - 00:45",
                  "business_date": "2025-05-14",
                  "source_datetime": "2025-05-13 13:49:22.204"
                },
            ]
        }
        expected_date = "2025-05-14"
        expected_prices = {
            "2025-05-14 00:15:00": 439.58,
            "2025-05-14 00:30:00": 449.58,
            "2025-05-14 00:45:00": 459.58,
        }

        cls_api_pse = api.ApiPse(self.log)
        status = cls_api_pse.get_pse_data("2025-05-14")

        self.assertTrue(status)
        self.assertTrue(hasattr(cls_api_pse, "rce_date"))
        self.assertEqual(expected_date, cls_api_pse.rce_date)
        self.assertTrue(hasattr(cls_api_pse, "rce_prices"))
        self.assertEqual(expected_prices, cls_api_pse.rce_prices)


if __name__ == "__main__":
    unittest.main()
