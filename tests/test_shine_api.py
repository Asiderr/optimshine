import io
import os
import requests
import logging
import unittest

import optimshine.shine_api as api
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
    def test_user_login(self, mock_post: requests.post):
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = (
            {"data": {"token": "xyz"}}
        )

        cls_api_shine = api.ApiShine(self.log)
        result = cls_api_shine.login_shine()
        self.assertTrue(hasattr(cls_api_shine, "token"))
        self.assertEqual(cls_api_shine.token, "xyz")
        self.assertTrue(result)

    @patch("requests.post")
    def test_user_login_wrong_password(self, mock_post: requests.post):
        stdio = io.StringIO()
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = (
            {"data": "Wrong password"}
        )

        handler = logging.StreamHandler(stream=stdio)
        self.log.addHandler(handler)
        cls_api_shine = api.ApiShine(self.log)

        result = cls_api_shine.login_shine()
        stdout = stdio.getvalue()

        self.assertFalse(result)
        self.assertIn("Login attempt failed. Wrong password", stdout)

    @patch("requests.post")
    def test_user_login_status_code(self, mock_post: requests.post):
        stdio = io.StringIO()
        mock_post.return_value.status_code = 501

        handler = logging.StreamHandler(stream=stdio)
        self.log.addHandler(handler)

        cls_api_shine = api.ApiShine(self.log)
        result = cls_api_shine.login_shine()
        stdout = stdio.getvalue()

        self.assertFalse(result)
        self.assertIn("Login attempt failed. Status code 501", stdout)

    def test_user_login_user_name(self):
        stdio = io.StringIO()
        handler = logging.StreamHandler(stream=stdio)
        self.log.addHandler(handler)
        os.environ["SHINE_USER"] = ""

        cls_api_shine = api.ApiShine(self.log)
        result = cls_api_shine.login_shine()
        stdout = stdio.getvalue()

        self.assertFalse(result)
        self.assertIn("Shine API user or password not set!", stdout)
        os.environ["SHINE_USER"] = "test"

    @patch("optimshine.shine_api.ApiShine._get_shine_api_url")
    def test_user_login_wrong_endpoint(self, mock_get_url):
        stdio = io.StringIO()
        handler = logging.StreamHandler(stream=stdio)
        self.log.addHandler(handler)
        mock_get_url.return_value = None

        cls_api_shine = api.ApiShine(self.log)
        result = cls_api_shine.login_shine()
        stdout = stdio.getvalue()

        self.assertFalse(result)
        self.assertIn("Parsing login API URL failed!", stdout)


if __name__ == "__main__":
    unittest.main()
