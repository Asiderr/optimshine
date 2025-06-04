import io
import logging
import unittest

from datetime import datetime, timedelta
from unittest.mock import call, MagicMock, patch
from zoneinfo import ZoneInfo

from optimshine.optim_shine import OptimShine


class TestOptimShine(unittest.TestCase):
    @patch('optimshine.optim_shine.sdnotify')
    def setUp(self, mock_sdnotify):
        mock_sdnotify.SystemdNotifier.return_value = MagicMock()

        self.cl = OptimShine("tests/.testenv")
        self.stdio = io.StringIO()
        handler = logging.StreamHandler(stream=self.stdio)
        self.cl.log.addHandler(handler)

    def tearDown(self):
        self.cl.log.handlers.clear()

    def test_shine_setup_login_failed(self):
        self.cl.login_shine = MagicMock()
        self.cl.login_shine.return_value = False

        with self.assertRaises(SystemExit) as test_exit:
            self.cl._shine_setup()

        stdout = self.stdio.getvalue()
        self.assertIn("Failed to login to Shine API", stdout)
        self.cl.login_shine.assert_called_once()
        self.assertEqual(test_exit.exception.code, 1)

    def test_shine_setup_get_plant_failed(self):
        self.cl.login_shine = MagicMock()
        self.cl.login_shine.return_value = True
        self.cl.get_plant_list = MagicMock()
        self.cl.get_plant_list.return_value = False

        with self.assertRaises(SystemExit) as test_exit:
            self.cl._shine_setup()

        stdout = self.stdio.getvalue()
        self.assertIn("Getting plant list failed.", stdout)
        self.cl.login_shine.assert_called_once()
        self.cl.get_plant_list.assert_called_once()
        self.assertEqual(test_exit.exception.code, 1)

    def test_shine_setup_none_plant_list(self):
        self.cl.login_shine = MagicMock()
        self.cl.login_shine.return_value = True
        self.cl.get_plant_list = MagicMock()
        self.cl.get_plant_list.return_value = True
        self.cl.plants_id = None

        with self.assertRaises(SystemExit) as test_exit:
            self.cl._shine_setup()

        stdout = self.stdio.getvalue()
        self.assertIn("Plants list is empty", stdout)
        self.cl.login_shine.assert_called_once()
        self.cl.get_plant_list.assert_called_once()
        self.assertEqual(test_exit.exception.code, 1)

    def test_shine_setup_wrong_plant(self):
        self.cl.login_shine = MagicMock()
        self.cl.login_shine.return_value = True
        self.cl.get_plant_list = MagicMock()
        self.cl.get_plant_list.return_value = True
        self.cl.plants_id = "Wrong data"

        with self.assertRaises(SystemExit) as test_exit:
            self.cl._shine_setup()

        stdout = self.stdio.getvalue()
        self.assertIn("test_plant not found in the plant list", stdout)
        self.cl.login_shine.assert_called_once()
        self.cl.get_plant_list.assert_called_once()
        self.assertEqual(test_exit.exception.code, 1)

    @patch("optimshine.optim_shine.os")
    def test_shine_setup_no_env_plant_one_plant_pass(self, mock_os):
        mock_os.getenv.return_value = None
        self.cl.login_shine = MagicMock()
        self.cl.login_shine.return_value = True
        self.cl.get_plant_list = MagicMock()
        self.cl.get_plant_list.return_value = True
        self.cl.plants_id = {"plant_name": {"id": "0000"}}
        self.cl._get_device_list = MagicMock()
        self.cl._get_device_list.return_value = True
        self.cl.device_list = ["1111"]

        self.cl._shine_setup()
        stdout = self.stdio.getvalue()

        self.assertIn("API Shine setup was successful", stdout)
        self.cl.login_shine.assert_called_once()
        self.cl.get_plant_list.assert_called_once()
        self.cl._get_device_list.assert_called_once_with("0000", "INV")
        self.assertEqual(self.cl.inverters, ["1111"])

    @patch("optimshine.optim_shine.os")
    def test_shine_setup_no_env_plant_many_plants(self, mock_os):
        mock_os.getenv.return_value = None
        self.cl.login_shine = MagicMock()
        self.cl.login_shine.return_value = True
        self.cl.get_plant_list = MagicMock()
        self.cl.get_plant_list.return_value = True
        self.cl.plants_id = {"plant_name1": {"id": "0000"},
                             "plant_name2": {"id": "2222"}}

        with self.assertRaises(SystemExit) as test_exit:
            self.cl._shine_setup()

        stdout = self.stdio.getvalue()
        self.assertIn("You must set SHINE_PLANT", stdout)
        self.cl.login_shine.assert_called_once()
        self.cl.get_plant_list.assert_called_once()
        self.assertEqual(test_exit.exception.code, 1)

    def test_shine_setup_get_device_list_failure(self):
        self.cl.login_shine = MagicMock()
        self.cl.login_shine.return_value = True
        self.cl.get_plant_list = MagicMock()
        self.cl.get_plant_list.return_value = True
        self.cl.plants_id = {"test_plant": {"id": "0000"},
                             "plant_name2": {"id": "2222"}}
        self.cl._get_device_list = MagicMock()
        self.cl._get_device_list.return_value = False

        with self.assertRaises(SystemExit) as test_exit:
            self.cl._shine_setup()

        stdout = self.stdio.getvalue()
        self.assertIn("Failed to get list of inverters", stdout)
        self.cl.login_shine.assert_called_once()
        self.cl.get_plant_list.assert_called_once()
        self.cl._get_device_list.assert_called_once_with("0000", "INV")
        self.assertEqual(test_exit.exception.code, 1)

    def test_shine_setup_empty_device_list(self):
        self.cl.login_shine = MagicMock()
        self.cl.login_shine.return_value = True
        self.cl.get_plant_list = MagicMock()
        self.cl.get_plant_list.return_value = True
        self.cl.plants_id = {"test_plant": {"id": "0000"},
                             "plant_name2": {"id": "2222"}}
        self.cl._get_device_list = MagicMock()
        self.cl._get_device_list.return_value = True
        self.cl.device_list = None

        with self.assertRaises(SystemExit) as test_exit:
            self.cl._shine_setup()

        stdout = self.stdio.getvalue()
        self.assertIn("No inverters found", stdout)
        self.cl.login_shine.assert_called_once()
        self.cl.get_plant_list.assert_called_once()
        self.cl._get_device_list.assert_called_once_with("0000", "INV")
        self.assertEqual(test_exit.exception.code, 1)

    def test_shine_setup_pass(self):
        self.cl.login_shine = MagicMock()
        self.cl.login_shine.return_value = True
        self.cl.get_plant_list = MagicMock()
        self.cl.get_plant_list.return_value = True
        self.cl.plants_id = {"test_plant": {"id": "0000"},
                             "plant_name2": {"id": "2222"}}
        self.cl._get_device_list = MagicMock()
        self.cl._get_device_list.return_value = True
        self.cl.device_list = ["1111"]

        self.cl._shine_setup()

        stdout = self.stdio.getvalue()
        self.assertIn("API Shine setup was successful", stdout)
        self.cl.login_shine.assert_called_once()
        self.cl.get_plant_list.assert_called_once()
        self.cl._get_device_list.assert_called_once_with("0000", "INV")
        self.assertEqual(self.cl.inverters, ["1111"])

    def test_check_weather_get_weather_data_fail(self):
        test_date = datetime(year=2025, month=6, day=4).strftime("%Y-%m-%d")
        self.cl.get_weather_data = MagicMock()
        self.cl.get_weather_data.return_value = False

        status = self.cl._check_weather("0.000", "0.000", test_date)

        stdout = self.stdio.getvalue()
        self.cl.get_weather_data.assert_called_once_with("0.000", "0.000",
                                                         test_date)
        self.assertIn("Weather forecast is not available", stdout)
        self.assertFalse(status)

    def test_check_weather_empty_weather_data(self):
        test_date = datetime(year=2025, month=6, day=4).strftime("%Y-%m-%d")
        self.cl.get_weather_data = MagicMock()
        self.cl.get_weather_data.return_value = True
        self.cl.weather_data = {"low_clouds_data": []}

        status = self.cl._check_weather("0.000", "0.000", test_date)

        self.cl.get_weather_data.assert_called_once_with("0.000", "0.000",
                                                         test_date)
        self.assertFalse(self.cl.not_cloudy)
        self.assertTrue(status)

    def test_check_weather_not_cloudy(self):
        test_date = datetime(year=2025, month=6, day=4).strftime("%Y-%m-%d")
        self.cl.get_weather_data = MagicMock()
        self.cl.get_weather_data.return_value = True
        self.cl.weather_data = {
            "low_clouds_data": [0.038, 0.172, 0.115, 0.9]
        }

        status = self.cl._check_weather("0.000", "0.000", test_date)

        self.cl.get_weather_data.assert_called_once_with("0.000", "0.000",
                                                         test_date)
        self.assertTrue(self.cl.not_cloudy)
        self.assertTrue(status)

    def test_check_weather_cloudy_50_50(self):
        test_date = datetime(year=2025, month=6, day=4).strftime("%Y-%m-%d")
        self.cl.get_weather_data = MagicMock()
        self.cl.get_weather_data.return_value = True
        self.cl.weather_data = {
            "low_clouds_data": [0.8, 0.8, 0.115, 0.164]
        }

        status = self.cl._check_weather("0.000", "0.000", test_date)

        self.cl.get_weather_data.assert_called_once_with("0.000", "0.000",
                                                         test_date)
        self.assertFalse(self.cl.not_cloudy)
        self.assertTrue(status)

    def test_check_weather_cloudy(self):
        test_date = datetime(year=2025, month=6, day=4).strftime("%Y-%m-%d")
        self.cl.get_weather_data = MagicMock()
        self.cl.get_weather_data.return_value = True
        self.cl.weather_data = {
            "low_clouds_data": [0.8, 0.8, 0.8, 0.115, 0.164]
        }

        status = self.cl._check_weather("0.000", "0.000", test_date)

        self.cl.get_weather_data.assert_called_once_with("0.000", "0.000",
                                                         test_date)
        self.assertFalse(self.cl.not_cloudy)
        self.assertTrue(status)

    def test_get_judge_factors_no_plant(self):
        status = self.cl._get_judge_factors()

        stdout = self.stdio.getvalue()
        self.assertIn("No plant info available", stdout)
        self.assertFalse(status)

    def test_get_judge_factors_check_weather_fail(self):
        self.cl._check_weather = MagicMock()
        self.cl._check_weather.return_value = False
        self.cl.plant = {"latitude": "0.0000", "longitude": "10.0000"}
        date = datetime.now().strftime("%Y-%m-%d")

        status = self.cl._get_judge_factors()

        stdout = self.stdio.getvalue()
        self.assertIn("Failed to check weather", stdout)
        self.cl._check_weather.assert_called_once_with("0.0000", "10.0000",
                                                       date)
        self.assertFalse(status)

    def test_get_judge_factors_get_pse_data_fail(self):
        self.cl._check_weather = MagicMock()
        self.cl._check_weather.return_value = True
        self.cl.get_pse_data = MagicMock()
        self.cl.get_pse_data.return_value = False
        self.cl.plant = {"latitude": "0.0000", "longitude": "10.0000"}
        date = datetime.now().strftime("%Y-%m-%d")
        self.cl.not_cloudy = False

        status = self.cl._get_judge_factors()

        stdout = self.stdio.getvalue()
        self.assertIn("Failed to get RCE prices", stdout)
        self.cl._check_weather.assert_called_once_with("0.0000", "10.0000",
                                                       date)
        self.cl.get_pse_data.assert_called_once_with(date)
        self.assertFalse(status)

    def test_get_judge_factors_pass(self):
        self.cl._check_weather = MagicMock()
        self.cl._check_weather.return_value = True
        self.cl.get_pse_data = MagicMock()
        self.cl.get_pse_data.return_value = True
        self.cl.plant = {"latitude": "0.0000", "longitude": "10.0000"}
        date = datetime.now().strftime("%Y-%m-%d")
        self.cl.not_cloudy = False
        self.cl.rce_prices = {
            "2025-05-14 00:15:00": 439.58,
            "2025-05-14 01:30:00": 449.58,
            "2025-05-14 02:45:00": 59.58,
        }
        expected_timestamp = datetime(
            year=2025,
            month=5,
            day=14,
            hour=2,
            minute=0,
            second=0,
            microsecond=0,
            tzinfo=ZoneInfo("Europe/Warsaw")
        ).timestamp()

        status = self.cl._get_judge_factors()

        stdout = self.stdio.getvalue()
        self.assertIn("Successfully obtained judge factors", stdout)
        self.cl._check_weather.assert_called_once_with("0.0000", "10.0000",
                                                       date)
        self.cl.get_pse_data.assert_called_once_with(date)
        self.assertTrue(status)
        self.assertEqual(self.cl.min_price, 59.58)
        self.assertEqual(self.cl.min_price_timestamp, expected_timestamp)

    def test_optim_charge_battery_reauthorization_failed(self):
        token_ttl_date = datetime.now() - timedelta(minutes=30)
        self.cl.token_ttl = token_ttl_date.timestamp()
        self.cl.login_shine = MagicMock()
        self.cl.login_shine.return_value = False
        with self.assertRaises(RuntimeError):
            self.cl.optim_charge_battery("INV", "test_mode")

        stdout = self.stdio.getvalue()
        self.assertIn("Authorization token has expired. Failed to login",
                      stdout)
        self.cl.login_shine.assert_called_once()

    def test_optim_charge_battery_wrong_mode(self):
        token_ttl_date = datetime.now() + timedelta(minutes=30)
        self.cl.token_ttl = token_ttl_date.timestamp()

        with self.assertRaises(AttributeError):
            self.cl.optim_charge_battery("INV", "test_mode")

        stdout = self.stdio.getvalue()
        self.assertIn("test_mode charge mode unknown", stdout)

    def test_optim_charge_battery_get_setting_value_failed(self):
        token_ttl_date = datetime.now() + timedelta(minutes=30)
        self.cl.token_ttl = token_ttl_date.timestamp()
        self.cl.get_setting_value = MagicMock()
        self.cl.get_setting_value.return_value = False

        with self.assertRaises(RuntimeError):
            self.cl.optim_charge_battery("INV", "normal_charge")

        stdout = self.stdio.getvalue()
        self.assertIn("Getting battery charge current failed", stdout)
        self.cl.get_setting_value.assert_called_once_with(
            "INV",
            "battery_charge_current"
        )

    def test_optim_charge_battery_same_value_pass(self):
        token_ttl_date = datetime.now() + timedelta(minutes=30)
        self.cl.token_ttl = token_ttl_date.timestamp()
        self.cl.get_setting_value = MagicMock()
        self.cl.get_setting_value.return_value = True
        self.cl.setting_value = 600

        status = self.cl.optim_charge_battery("INV", "normal_charge")

        stdout = self.stdio.getvalue()
        self.assertIn("Correct charge current value is already set", stdout)
        self.cl.get_setting_value.assert_called_once_with(
            "INV",
            "battery_charge_current"
        )
        self.assertTrue(status)

    def test_optim_charge_battery_set_charge_current_failed(self):
        token_ttl_date = datetime.now() + timedelta(minutes=30)
        self.cl.token_ttl = token_ttl_date.timestamp()
        self.cl.get_setting_value = MagicMock()
        self.cl.get_setting_value.return_value = True
        self.cl.setting_value = 10
        self.cl.set_charge_current = MagicMock()
        self.cl.set_charge_current.return_value = False

        with self.assertRaises(RuntimeError):
            self.cl.optim_charge_battery("INV", "normal_charge")

        stdout = self.stdio.getvalue()
        self.assertIn("Failed to set battery charge current", stdout)
        self.cl.get_setting_value.assert_called_once_with(
            "INV",
            "battery_charge_current"
        )
        self.cl.set_charge_current.assert_called_once_with("INV", 60)

    def test_optim_charge_battery_get_setting_value_validation_failed(self):
        token_ttl_date = datetime.now() + timedelta(minutes=30)
        self.cl.token_ttl = token_ttl_date.timestamp()
        self.cl.get_setting_value = MagicMock()
        self.cl.get_setting_value.side_effect = [True, False]
        self.cl.setting_value = 10
        self.cl.set_charge_current = MagicMock()
        self.cl.set_charge_current.return_value = True

        with self.assertRaises(RuntimeError):
            self.cl.optim_charge_battery("INV", "normal_charge")

        stdout = self.stdio.getvalue()
        self.assertIn("failed (Validation)", stdout)
        self.cl.get_setting_value.assert_has_calls([
            call("INV", "battery_charge_current"),
            call("INV", "battery_charge_current"),
        ])
        self.cl.set_charge_current.assert_called_once_with("INV", 60)

    def side_effect_set_charge_current_10(self, _, __):
        self.cl.setting_value = 100
        return True

    def side_effect_set_charge_current_60(self, _, __):
        self.cl.setting_value = 600
        return True

    def test_optim_charge_battery_wrong_value_afeter_set(self):
        token_ttl_date = datetime.now() + timedelta(minutes=30)
        self.cl.token_ttl = token_ttl_date.timestamp()
        self.cl.get_setting_value = MagicMock()
        self.cl.get_setting_value.return_value = True
        self.cl.setting_value = 10
        self.cl.set_charge_current = MagicMock()
        self.cl.set_charge_current.side_effect = (
            self.side_effect_set_charge_current_10
        )

        with self.assertRaises(RuntimeError):
            self.cl.optim_charge_battery("INV", "normal_charge")

        stdout = self.stdio.getvalue()
        self.assertIn("Wrong current value", stdout)
        self.cl.get_setting_value.assert_has_calls([
            call("INV", "battery_charge_current"),
            call("INV", "battery_charge_current"),
        ])
        self.cl.set_charge_current.assert_called_once_with("INV", 60)

    def test_optim_charge_battery_pass(self):
        token_ttl_date = datetime.now() + timedelta(minutes=30)
        self.cl.token_ttl = token_ttl_date.timestamp()
        self.cl.get_setting_value = MagicMock()
        self.cl.get_setting_value.return_value = True
        self.cl.setting_value = 10
        self.cl.set_charge_current = MagicMock()
        self.cl.set_charge_current.side_effect = (
            self.side_effect_set_charge_current_60
        )

        status = self.cl.optim_charge_battery("INV", "normal_charge")

        stdout = self.stdio.getvalue()
        self.assertIn("Battery charging optimization was successful", stdout)
        self.cl.get_setting_value.assert_has_calls([
            call("INV", "battery_charge_current"),
            call("INV", "battery_charge_current"),
        ])
        self.cl.set_charge_current.assert_called_once_with("INV", 60)
        self.assertTrue(status)

    def test_optim_soc_check_reauthorization_failed(self):
        token_ttl_date = datetime.now() - timedelta(minutes=30)
        self.cl.token_ttl = token_ttl_date.timestamp()
        self.cl.login_shine = MagicMock()
        self.cl.login_shine.return_value = False
        with self.assertRaises(RuntimeError):
            self.cl.optim_soc_check("INV")

        stdout = self.stdio.getvalue()
        self.assertIn("Authorization token has expired. Failed to login",
                      stdout)
        self.cl.login_shine.assert_called_once()

    def test_optim_soc_check_get_device_value_failed(self):
        token_ttl_date = datetime.now() + timedelta(minutes=30)
        self.cl.token_ttl = token_ttl_date.timestamp()
        self.cl.get_device_value = MagicMock()
        self.cl.get_device_value.return_value = False

        with self.assertRaises(RuntimeError):
            self.cl.optim_soc_check("INV")

        stdout = self.stdio.getvalue()
        self.assertIn("Getting battery state of charge failed", stdout)
        self.cl.get_device_value.assert_called_once_with("INV", "battery_soc")

    def test_optim_soc_check_soc_more_than_50_pass(self):
        token_ttl_date = datetime.now() + timedelta(minutes=30)
        self.cl.token_ttl = token_ttl_date.timestamp()
        self.cl.get_device_value = MagicMock()
        self.cl.get_device_value.return_value = True
        self.cl.optim_charge_battery = MagicMock()
        self.cl.optim_charge_battery.return_value = True
        self.cl.device_value = 51

        status = self.cl.optim_soc_check("INV")

        stdout = self.stdio.getvalue()
        self.assertIn("Battery is ready for optimization. No charge mode set",
                      stdout)
        self.cl.get_device_value.assert_called_once_with("INV", "battery_soc")
        self.cl.optim_charge_battery.assert_called_once_with("INV",
                                                             "no_charge")
        self.assertTrue(status)

    def test_optim_soc_check_soc_more_less_50_scheduled_pass(self):
        token_ttl_date = datetime.now() + timedelta(minutes=30)
        self.cl.token_ttl = token_ttl_date.timestamp()
        self.cl.get_device_value = MagicMock()
        self.cl.get_device_value.return_value = True
        self.cl.optim_charge_battery = MagicMock()
        self.cl.optim_charge_battery.return_value = True
        self.cl.device_value = 49
        self.cl.optim_date = datetime.now() + timedelta(minutes=120)

        self.cl.scheduler.start()
        status = self.cl.optim_soc_check("INV")
        self.cl.scheduler.shutdown()

        stdout = self.stdio.getvalue()
        self.assertIn("Battery needs to be charge before optimization",
                      stdout)
        self.assertIn("Job ID: optim_soc_check_inv_INV, Next run:", stdout)
        self.cl.get_device_value.assert_called_once_with("INV", "battery_soc")
        self.cl.optim_charge_battery.assert_called_once_with("INV",
                                                             "slow_charge")
        self.assertTrue(status)

    def test_optim_soc_check_soc_more_less_50_not_scheduled_pass(self):
        token_ttl_date = datetime.now() + timedelta(minutes=30)
        self.cl.token_ttl = token_ttl_date.timestamp()
        self.cl.get_device_value = MagicMock()
        self.cl.get_device_value.return_value = True
        self.cl.optim_charge_battery = MagicMock()
        self.cl.optim_charge_battery.return_value = True
        self.cl.device_value = 49
        self.cl.optim_date = datetime.now() + timedelta(minutes=26)

        self.cl.scheduler.start()
        status = self.cl.optim_soc_check("INV")
        self.cl.scheduler.shutdown()

        stdout = self.stdio.getvalue()
        self.assertIn("Battery needs to be charge before optimization",
                      stdout)
        self.assertIn("No scheduled jobs", stdout)
        self.cl.get_device_value.assert_called_once_with("INV", "battery_soc")
        self.cl.optim_charge_battery.assert_called_once_with("INV",
                                                             "slow_charge")
        self.assertTrue(status)


if __name__ == "__main__":
    unittest.main()
