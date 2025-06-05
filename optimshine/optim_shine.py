#!/usr/bin/env python

import os
import time
import sdnotify

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from optimshine.api_shine import ApiShine
from optimshine.api_weather import ApiWeather
from optimshine.api_pse import ApiPse
from optimshine.optim_config import OptimConfig


CHARGE_MODES = {
    "no_charge": 1,
    "slow_charge": 30,
    "normal_charge": 60,
    "fast_charge": 90,
}


class OptimShine(OptimConfig, ApiPse, ApiShine, ApiWeather):
    def __init__(self):
        self.judge_date: datetime = None
        self.soc_check_date: datetime = None
        self.optim = False
        self.optim_date: datetime = None

        self.notifier = sdnotify.SystemdNotifier()
        self.notifier.notify("READY=1")
        self.logger_setup()
        self.envs_setup()
        self.scheduler_setup()

    def _shine_setup(self):
        self.log.info("Trying to login to Shine API")
        if not self.login_shine():
            self.log.critical("Failed to login to Shine API. Exiting...")
            exit(1)

        self.log.info("Trying to get plant list")
        if not self.get_plant_list():
            self.log.critical("Getting plant list failed. Exiting...")
            exit(1)

        if not self.plants_id:
            self.log.critical("Plants list is empty. Exiting...")
            exit(1)

        shine_plant = os.getenv("SHINE_PLANT")

        if shine_plant:
            try:
                self.plant = self.plants_id[shine_plant]
            except KeyError:
                self.log.critical(f"{shine_plant} not found in the plant "
                                  "list. Check your plant name in Monitoring->"
                                  "Plant. Exiting...")
                exit(1)
        elif not shine_plant and len(self.plants_id) == 1:
            self.plant = next(iter(self.plants_id.values()))
        else:
            self.log.critical("You must set SHINE_PLANT if you have more than"
                              " one plant. Exiting...")
            exit(1)

        self.log.info("Trying to get inverter list")
        if not self._get_device_list(self.plant["id"], "INV"):
            self.log.critical("Failed to get list of inverters. Exiting...")
            exit(1)

        if not self.device_list:
            self.log.critical("No inverters found. Exiting...")
            exit(1)

        self.inverters = self.device_list.copy()
        self.device_list = None

    def _check_weather(self, latitude, longitude, date):
        self.not_cloudy = False
        not_cloudy_hours = 0

        if not self.get_weather_data(latitude, longitude, date):
            self.log.error("Weather forecast is not available")
            return False

        for sample in self.weather_data["low_clouds_data"]:
            if sample < 0.75:
                not_cloudy_hours += 1

        if not_cloudy_hours > len(self.weather_data["low_clouds_data"])/2:
            self.not_cloudy = True

        return True

    def _get_judge_factors(self):
        if not hasattr(self, "plant"):
            self.log.error("No plant info available")
            return False

        date = datetime.now().strftime("%Y-%m-%d")

        self.log.debug("Trying to get weather data")
        if not self._check_weather(self.plant["longitude"],
                                   self.plant["latitude"],
                                   date):
            self.log.error("Failed to check weather")
            return False
        self.log.debug(f"not_cloudy flag: {self.not_cloudy}")

        self.log.debug("Trying to get PSE data")
        if not self.get_pse_data(date):
            self.log.error("Failed to get RCE prices")
            return False

        self.min_price = next(iter(self.rce_prices.values()))
        for quarter, price in self.rce_prices.items():
            if price < self.min_price:
                time = datetime.strptime(quarter, "%Y-%m-%d %H:%M:%S").replace(
                    tzinfo=ZoneInfo("Europe/Warsaw")
                ).astimezone(ZoneInfo("UTC"))
                self.min_price_timestamp = self._get_timestamp_hour(
                    time.strftime("%Y-%m-%d"),
                    time.strftime("%I:%M:%S %p")
                )
                self.min_price = price

        self.log.debug(f"min_price_timestamp: {self.min_price_timestamp}")
        self.log.debug(f"min_price: {self.min_price}")

        self.log.info("Successfully obtained judge factors")
        return True

    def optim_charge_battery(self, inverter, mode):
        time_now = datetime.now().timestamp()
        self.log.debug("Checking if token is valid")
        if self.token_ttl < time_now and not self.login_shine():
            self.log.error("Authorization token has expired. "
                           "Failed to login to Shine API")
            raise RuntimeError

        self.log.debug(f"Battery charging mode: {mode}")
        try:
            target_charge_current = CHARGE_MODES[mode]
        except KeyError:
            self.log.error(f"{mode} charge mode unknown")
            raise RuntimeError

        self.log.debug("Getting battery charge current value")
        if not self.get_setting_value(inverter, "battery_charge_current"):
            self.log.error("Getting battery charge current failed")
            raise RuntimeError

        setting_charge_current = self.setting_value/10
        self.setting_value = None
        self.log.debug("Battery charge current value: "
                       f"{setting_charge_current} A")

        if setting_charge_current == target_charge_current:
            self.log.info("Correct charge current value is already set. "
                          "Battery charging optimization was successful")
            return True

        if not self.set_charge_current(inverter, target_charge_current):
            self.log.error("Failed to set battery charge current")
            raise RuntimeError

        if not self.get_setting_value(inverter, "battery_charge_current"):
            self.log.error("Getting battery charge current failed "
                           "(Validation)")
            raise RuntimeError

        setting_charge_current = self.setting_value/10
        self.setting_value = None
        self.log.debug("Battery charge current value: "
                       f"{setting_charge_current} A")

        if not setting_charge_current == target_charge_current:
            self.log.error("Failed to set battery charge current. "
                           "Wrong current value")
            raise RuntimeError
        self.log.info("Battery charging optimization was successful")
        return True

    def optim_soc_check(self, inverter):
        """
        if less than 50% > charge current 30A + check soc in 30 min,
        if more charge current 1A (no charge)"
        """
        time_now = datetime.now().timestamp()
        self.log.debug("Checking if token is valid")
        if self.token_ttl < time_now and not self.login_shine():
            self.log.error("Authorization token has expired. "
                           "Failed to login to Shine API")
            raise RuntimeError

        self.log.debug("Getting battery state of charge")
        if not self._get_device_value(inverter, "battery_soc"):
            self.log.error("Getting battery state of charge failed")
            raise RuntimeError

        soc_value = float(self.device_value)
        self.device_value = None
        self.log.debug(f"Battery SOC: {soc_value}%")

        if soc_value < 50:
            self.log.info("Battery needs to be charge before optimization.")
            self.optim_charge_battery(inverter, "slow_charge")
        else:
            self.optim_charge_battery(inverter, "no_charge")
            self.log.info("Battery is ready for optimization. "
                          "No charge mode set")
            return True

        self.log.info("Scheduling next soc check in 30 minutes")
        next_soc_check_date = time_now + 1800
        if next_soc_check_date < (self.optim_date.timestamp()-180):
            self.soc_check_date = next_soc_check_date
            self.scheduler.add_job(
                self.optim_soc_check,
                trigger="date",
                run_date=self.soc_check_date,
                id=f"optim_soc_check_inv_{inverter}",
                replace_existing=True,
                kwargs={"inverter": inverter}
            )
        return True

    def _optim_strategy(self):
        if not self.optim:
            self.log.info("Optimization not needed")
            return True

        if not self.optim_date or not self.soc_check_date:
            self.log.error("Optimization dates not set")
            return False

        if not self.min_price:
            self.log.error("RCE minimal price price not set")
            return False

        if not hasattr(self, "inverters") or not self.inverters:
            self.log.error("No inverter list found")
            return False

        if self.min_price < 0:
            charging_mode = "fast_charge"
        else:
            charging_mode = "normal_charge"

        time_now = datetime.now().timestamp()
        if time_now > self.optim_date.timestamp():
            self.log.warning("Optimization time was missed")
            self.optim = False
            self.soc_check_date = None
            self.optim_date = None
            return True

        if time_now > self.soc_check_date.timestamp():
            self.soc_check_date = (datetime.fromtimestamp(time_now) +
                                   timedelta(seconds=30))

        for inverter in self.inverters:
            self.log.info("Setting optimization strategy for inverter nr"
                          f" {inverter}")
            if not (self.soc_check_date.timestamp() >
                    (self.optim_date.timestamp()-180)):
                self.scheduler.add_job(
                    self.optim_soc_check,
                    trigger="date",
                    run_date=self.soc_check_date,
                    id=f"optim_soc_check_inv_{inverter}",
                    replace_existing=True,
                    kwargs={"inverter": inverter}
                )
            self.scheduler.add_job(
                self.optim_charge_battery,
                trigger="date",
                run_date=self.optim_date,
                id=f"optim_charge_battery_inv_{inverter}",
                replace_existing=True,
                kwargs={"inverter": inverter, "mode": charging_mode}
            )
            if not (self.weather_data["sunrise_time"] >=
                    self.weather_data["sunset_time"]):
                self.scheduler.add_job(
                    self.optim_charge_battery,
                    trigger="date",
                    run_date=datetime.fromtimestamp(
                        self.weather_data["sunset_time"]
                    ),
                    id=f"eod_charge_battery_inv_{inverter}",
                    replace_existing=True,
                    kwargs={
                        "inverter": inverter,
                        "mode": "slow_charge",
                    }
                )
        return True

    def optim_judge(self):
        self.log.info("Getting weather data and energy prices")
        if not self._get_judge_factors():
            self.log.warning("Failed to get judge factors")
            self.judge_date += timedelta(minutes=30)
            self.log.info(
                "Rescheduling optimization judge to "
                f"{self.judge_date.strftime('%d-%m-%Y %H:%M')}"
            )
            self.scheduler.add_job(
                self.optim_judge,
                trigger="date",
                run_date=self.judge_date,
                id="optim_judge",
                replace_existing=True)
            raise RuntimeError

        if self.judge_date.timestamp() > self.weather_data["sunrise_time"]:
            self.soc_check_date = self.judge_date + timedelta(minutes=2)
        else:
            self.soc_check_date = datetime.fromtimestamp(
                self.weather_data["sunrise_time"]
            )

        if self.not_cloudy:
            # https://www.youtube.com/watch?v=-Hv8fj8hQlE
            self.log.info("It'll be sunny day")
            self.optim = True
            self.optim_date = datetime.fromtimestamp(self.min_price_timestamp)
        else:
            # https://www.youtube.com/watch?v=aSLZFdqwh7E
            self.log.info("It'll be cloudy day")
            self.optim = False
            self.optim_date = None
            self.soc_check_date = None

        self.log.debug(f"Optim flag: {self.optim}")
        self.log.debug(f"Optim date: {self.optim_date}")
        self.log.debug(f"State of charge check date: {self.soc_check_date}")
        self.log.info("Setting up optimization strategy")
        if not self._optim_strategy():
            self.log.error("Setting optimization strategy failed")
            raise RuntimeError

        self.log.info("Scheduling tomorrow's optimization judge")
        # Based on publication dates tomorrow 4:06AM UTC

        self.judge_date = (
            datetime.now().astimezone(ZoneInfo("UTC")).replace(
                hour=4, minute=6, second=0, microsecond=0
            ) + timedelta(days=1)
        )
        self.scheduler.add_job(
            self.optim_judge,
            trigger="date",
            run_date=self.judge_date,
            id="optim_judge",
            replace_existing=True
        )

    def optim_main(self):
        self._shine_setup()

        time_now = datetime.now().astimezone(ZoneInfo("UTC"))
        self.judge_date = time_now.replace(
            hour=4, minute=6, second=0, microsecond=0
        )
        if time_now.timestamp() > self.judge_date.timestamp():
            self.judge_date += timedelta(days=1)

        self.log.info("Scheduling optimization judge to "
                      f"{self.judge_date.strftime('%d:%m:%Y %H:%M')}")
        self.scheduler.add_job(
            self.optim_judge,
            trigger="date",
            run_date=self.judge_date,
            id="optim_judge",
        )
        self.scheduler.start()

        while True:
            if (not self.scheduler.get_jobs() and not self.running_jobs):
                self.log.critical("No jobs scheduled. Exiting...")
                exit(1)
            self.notifier.notify("WATCHDOG=1")
            time.sleep(5)


if __name__ == "__main__":
    cls_optim = OptimShine()
    cls_optim.optim_main()
