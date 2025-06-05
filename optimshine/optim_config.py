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
    """
    A class to configure the Optim Shine project.
    """
    def logger_setup(self):
        """
        Sets up the logger with a colored output format.
        """
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
        """
        Sets up the environment by loading variables from a specified .env
        file.

        Args:
            envpath (str, optional): The path to the .env file.
                                     Defaults to ".env".

        Returns:
            bool: True if the environment was set up successfully,
                  False otherwise.
        """
        if not hasattr(self, "log"):
            print("Logger not found!")
            return False

        if not find_dotenv(filename=envpath):
            self.log.error(f"Env file not found at {envpath}")
            return False

        load_dotenv(envpath)
        return True

    def _job_running_listener(self, event):
        """
        Listener for job running events. Updates the state of missed and
        running jobs.

        Args:
            event: An object containing information about the job event,
                   including job_id.
        """
        if event.job_id in self.missed_jobs:
            self.missed_jobs.discard(event.job_id)
        else:
            self.running_jobs.add(event.job_id)

    def _job_missed_listener(self, event):
        """
        Listener for missed job events. If the job ID is not in the list
        of running jobs, it adds the job ID to the set of missed jobs.
        If the job ID is found in the running jobs, it removes the job ID
        from the running jobs to prevent race condition when scheduler
        is not started.

        Args:
            event: An event object containing information about the job event,
                   including the job_id attribute.
        """
        if event.job_id not in self.running_jobs:
            self.missed_jobs.add(event.job_id)
        else:
            self.running_jobs.discard(event.job_id)

    def _job_finished_listener(self, event):
        """
        Listener method that is called when a job finishes.
        This method removes the finished job's ID from the set of running jobs.

        Args:
            event: An object containing information about the finished job,
                   including the job_id of the completed job.
        """
        self.running_jobs.discard(event.job_id)

    def _job_error_listener(self, event):
        """
        Listener for job error events. It removes
        the job ID from the running jobs set and logs an error message.

        Args:
            event: An object containing information about the job event,
                   including the job_id of the finished job.
        """
        self.running_jobs.discard(event.job_id)
        self.log.error(f"{event.job_id} job finished with error")

    def _signal_handler(self, signum, _):
        """
        Handles OS signals to gracefully shut down the scheduler.

        This method is called when an OS signal is received. It logs the
        signal number and initiates the shutdown process for the scheduler.
        If there are currently running jobs, it waits for them to finish
        before shutting down the scheduler.

        Args:
            signum (int): The signal number that was caught.
            _: Unused parameter for the signal handler.
        """
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
        """
        Sets up the job scheduler with necessary listeners and signal handlers.

        This method initializes the BackgroundScheduler, sets up sets to track
        running and missed jobs, and adds listeners for job events such as
        submission, execution, and errors. It also configures signal handlers
        for graceful shutdown on SIGINT and SIGTERM signals.
        """
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
        """
        Lists all scheduled jobs in the scheduler.
        """
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
