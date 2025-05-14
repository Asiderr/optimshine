import datetime
import io
import unittest
import logging

import optimshine.api_common as api
import optimshine.optim_config as config

from freezegun import freeze_time
from unittest.mock import patch


class TestApiShine(unittest.TestCase):
    def setUp(self):
        cls_optim_config = config.OptimConfig()
        cls_optim_config.logger_setup()
        self.log = cls_optim_config.log
        cls_optim_config.envs_setup("tests/.testenv")

    def tearDown(self):
        self.log.handlers.clear()

    @patch("requests.post")
    def test_api_post_request(self, mock_post):
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = (
            {"data": "Success"}
        )

        cls_common_api = api.ApiCommon(self.log)
        response = cls_common_api.api_post_request(
            "test_url",
            {"test_request": "request"},
            "test_token"
        )
        self.assertEqual(response, {"data": "Success"})

    @patch("requests.post")
    def test_user_login_status_code(self, mock_post):
        stdio = io.StringIO()
        mock_post.return_value.status_code = 501

        handler = logging.StreamHandler(stream=stdio)
        self.log.addHandler(handler)

        cls_common_api = api.ApiCommon(self.log)
        response = cls_common_api.api_post_request(
            "test_url",
            {"test_request": "request"},
            "test_token"
        )
        stdout = stdio.getvalue()

        self.assertIsNone(response)
        self.assertIn("API post failed. Status code 501", stdout)

    @patch("requests.get")
    def test_api_get_request(self, mock_get):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = (
            {"data": "Success"}
        )

        cls_common_api = api.ApiCommon(self.log)
        response = cls_common_api.api_get_request("test_url")
        self.assertEqual(response, {"data": "Success"})

    @patch("requests.get")
    def test_api_get_request_status_code(self, mock_get):
        mock_get.return_value.status_code = 501

        cls_common_api = api.ApiCommon(self.log)
        response = cls_common_api.api_get_request("test_url")
        self.assertIsNone(response)

    @freeze_time("2025-05-15 00:55:00")
    def test_get_request_time_no_delta(self, ):
        cls_common_api = api.ApiCommon(self.log)
        time_now = cls_common_api.get_request_time()

        self.assertEqual("2025-05-15 00:55:00", time_now)

    @freeze_time("2025-05-15 00:55:00")
    def test_get_request_time_past_delta(self, ):
        cls_common_api = api.ApiCommon(self.log)
        time_now = cls_common_api.get_request_time(datetime.timedelta(days=1))

        self.assertEqual("2025-05-14 00:55:00", time_now)

    @freeze_time("2025-05-15 00:55:00")
    def test_get_request_time_future_delta(self, ):
        cls_common_api = api.ApiCommon(self.log)
        time_now = cls_common_api.get_request_time(datetime.timedelta(days=1),
                                                   future=True)

        self.assertEqual("2025-05-16 00:55:00", time_now)


if __name__ == "__main__":
    unittest.main()
