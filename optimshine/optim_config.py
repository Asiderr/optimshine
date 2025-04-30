#!/usr/bin/env python
import colorlog
from dotenv import load_dotenv, find_dotenv


class OptimConfig:
    def logger_setup(self):
        handler = colorlog.StreamHandler()
        handler.setFormatter(colorlog.ColoredFormatter(
            "%(asctime)s [%(levelname)s] - %(log_color)s%(message)s%(reset)s",
            log_colors={
                "DEBUG": "cyan",
                "INFO": "blue",
                "WARNING": "yellow",
                "ERROR": "bold_red",
            }
        ))

        self.log = colorlog.getLogger()
        self.log.setLevel(colorlog.DEBUG)
        self.log.addHandler(handler)

    def envs_setup(self, envpath=".env"):
        if not hasattr(self, "log"):
            print("Logger not found!")
            return False

        if not find_dotenv(filename=envpath):
            self.log.error(f"Env file not found at {envpath}")
            return False

        load_dotenv(envpath)
        return True
