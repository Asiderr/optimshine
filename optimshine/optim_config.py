#!/usr/bin/env python
import colorlog
import sys
import time

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.events import (
    EVENT_JOB_EXECUTED,
    EVENT_JOB_ERROR,
    EVENT_JOB_SUBMITTED,
    EVENT_JOB_MISSED,
)
from dotenv import load_dotenv, find_dotenv
from signal import signal, SIGINT, SIGTERM


class OptimConfig:
    def logger_setup(self):
        handler = colorlog.StreamHandler()
        handler.setFormatter(colorlog.ColoredFormatter(
            "%(asctime)s [%(levelname)s] - %(log_color)s%(message)s%(reset)s",
            log_colors={
                "DEBUG": "cyan",
                "INFO": "green",
                "WARNING": "yellow",
                "ERROR": "red",
                "CRITICAL": "bold_red",
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

    def _job_running_listener(self, event):
        if event.job_id in self.missed_jobs:
            self.missed_jobs.discard(event.job_id)
        else:
            self.running_jobs.add(event.job_id)

    def _job_missed_listener(self, event):
        # Prevent race condition between submitting and missing events
        if event.job_id not in self.running_jobs:
            self.missed_jobs.add(event.job_id)
        else:
            self.running_jobs.discard(event.job_id)

    def _job_finished_listener(self, event):
        self.running_jobs.discard(event.job_id)

    def _job_error_listener(self, event):
        self.running_jobs.discard(event.job_id)
        self.log.error(f"{event.job_id} job finished with error")

    def _signal_handler(self, signum, _):
        self.log.warning(f"OS signal caught (num: {signum}), scheduler "
                         "shutdown requested")
        if self.running_jobs:
            self.log.warning(
                f"Finishing currently running jobs: {self.running_jobs}"
            )
            while self.running_jobs:
                time.sleep(5)
        self.scheduler.shutdown()
        self.log.info("Scheduler shutdown was successful, exiting")
        sys.exit(0)

    def scheduler_setup(self):
        self.scheduler = BackgroundScheduler()
        self.running_jobs = set()
        self.missed_jobs = set()
        self.scheduler.add_listener(self._job_running_listener,
                                    EVENT_JOB_SUBMITTED)
        self.scheduler.add_listener(self._job_missed_listener,
                                    EVENT_JOB_MISSED)
        self.scheduler.add_listener(self._job_finished_listener,
                                    EVENT_JOB_EXECUTED)
        self.scheduler.add_listener(self._job_error_listener,
                                    EVENT_JOB_ERROR)
        signal(SIGINT, self._signal_handler)
        signal(SIGTERM, self._signal_handler)

    def scheduler_list_jobs(self):
        if not hasattr(self, "scheduler"):
            self.log.error("Scheduler not initialized")
            self.log.warning("Cannot list scheduled jobs")
            return

        jobs = self.scheduler.get_jobs()

        if not jobs:
            self.log.warning("No scheduled jobs")
            return

        self.log.debug("----------- List of jobs ------------")
        for job in jobs:
            self.log.debug(f"Job ID: {job.id}, Next run: {job.next_run_time}")
        self.log.debug("-------------------------------------")
