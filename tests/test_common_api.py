import io
import unittest
import logging

import optimshine.common_api as api
import optimshine.optim_config as config

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

        cls_common_api = api.CommonApi(self.log)
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

        cls_common_api = api.CommonApi(self.log)
        response = cls_common_api.api_post_request(
            "test_url",
            {"test_request": "request"},
            "test_token"
        )
        stdout = stdio.getvalue()

        self.assertIsNone(response)
        self.assertIn("API post failed. Status code 501", stdout)


if __name__ == "__main__":
    unittest.main()
