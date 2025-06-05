#!/usr/bin/env python
#
# Copyright 2025 Norbert Kamiński <norbert.kaminski@xarium.world>
#
# SPDX-License-Identifier: LGPL-3.0-or-later
#

import io
import logging
import os
import threading
import time
import unittest

from apscheduler.events import (
    EVENT_JOB_EXECUTED,
    EVENT_JOB_ERROR,
    EVENT_JOB_SUBMITTED,
    EVENT_JOB_MISSED,
)
from logging import RootLogger
from unittest.mock import call, Mock, MagicMock, patch
from optimshine.optim_config import OptimConfig
from signal import SIGINT, SIGTERM


class TestOptimConfig(unittest.TestCase):
    def test_loger_setup(self):
        cl = OptimConfig()
        cl.logger_setup()
        self.assertTrue(isinstance(cl.log, RootLogger),
                        msg=f"Log type is wrong ({type(cl.log).__name__})")
        cl.log.handlers.clear()

    def test_envs_setup_no_logger(self):
        cl = OptimConfig()
        result = cl.envs_setup()
        self.assertFalse(result)

    def test_envs_setup_wrong_envpath(self):
        cl = OptimConfig()
        cl.logger_setup()
        stdio = io.StringIO()
        handler = logging.StreamHandler(stream=stdio)
        cl.log.addHandler(handler)
        result = cl.envs_setup("wrong")
        stdout = stdio.getvalue()
        self.assertFalse(result)
        self.assertIn("Env file not found at wrong", stdout)
        cl.log.handlers.clear()

    def test_envs_setup_pass(self):
        cl = OptimConfig()
        cl.logger_setup()
        result = cl.envs_setup("tests/.testenv")
        self.assertTrue(result)
        testvar = os.getenv("TESTVAR")
        self.assertEqual(testvar, "test")
        cl.log.handlers.clear()

    def test_job_running_listener_missed_jobs(self):
        event = Mock()
        event.job_id = "test_job_id"
        cl = OptimConfig()
        cl.missed_jobs = set()
        cl.running_jobs = set()
        cl.missed_jobs.add("test_job_id")
        cl._job_running_listener(event)
        self.assertSetEqual(cl.missed_jobs, set())

    def test_job_running_listener_running_jobs(self):
        event = Mock()
        event.job_id = "test_job_id"
        cl = OptimConfig()
        cl.missed_jobs = set()
        cl.running_jobs = set()
        cl._job_running_listener(event)
        self.assertIn("test_job_id", cl.running_jobs)

    def test_job_missed_listener_running_jobs(self):
        event = Mock()
        event.job_id = "test_job_id"
        cl = OptimConfig()
        cl.missed_jobs = set()
        cl.running_jobs = set()
        cl.running_jobs.add("test_job_id")
        cl._job_missed_listener(event)
        self.assertSetEqual(cl.running_jobs, set())

    def test_job_missed_listener_missed_jobs(self):
        event = Mock()
        event.job_id = "test_job_id"
        cl = OptimConfig()
        cl.missed_jobs = set()
        cl.running_jobs = set()
        cl._job_missed_listener(event)
        self.assertIn("test_job_id", cl.missed_jobs)

    def test_job_finished_listener(self):
        event = Mock()
        event.job_id = "test_job_id"
        cl = OptimConfig()
        cl.running_jobs = set()
        cl.running_jobs.add("test_job_id")
        cl._job_finished_listener(event)
        self.assertSetEqual(cl.running_jobs, set())

    def test_job_error_listener(self):
        cl = OptimConfig()
        cl.logger_setup()
        stdio = io.StringIO()
        handler = logging.StreamHandler(stream=stdio)
        cl.log.addHandler(handler)

        event = Mock()
        event.job_id = "test_job_id"

        cl.running_jobs = set()
        cl.running_jobs.add("test_job_id")
        cl._job_error_listener(event)
        stdout = stdio.getvalue()
        self.assertSetEqual(cl.running_jobs, set())
        self.assertIn("test_job_id job finished with error", stdout)
        cl.log.handlers.clear()

    @patch('sys.exit')
    def test_signal_handler_running_jobs_none(self, mock_exit):
        cl = OptimConfig()
        cl.scheduler = Mock()
        cl.logger_setup()
        stdio = io.StringIO()
        handler = logging.StreamHandler(stream=stdio)
        cl.log.addHandler(handler)

        cl.running_jobs = None
        cl._signal_handler(2, "")
        stdout = stdio.getvalue()

        cl.log.handlers.clear()
        self.assertIn("OS signal caught (num: 2)", stdout)
        mock_exit.assert_called_once_with(0)

    @patch('sys.exit')
    def test_signal_handler_running_jobs(self, mock_exit):
        cl = OptimConfig()
        cl.scheduler = Mock()
        cl.logger_setup()
        cl.running_jobs = ["test_job"]
        stdio = io.StringIO()
        handler = logging.StreamHandler(stream=stdio)
        cl.log.addHandler(handler)

        thread = threading.Thread(target=cl._signal_handler, args=(2, ""))
        thread.start()
        time.sleep(2)
        cl.running_jobs = []
        thread.join()
        stdout = stdio.getvalue()

        cl.log.handlers.clear()
        self.assertIn("Finishing currently running jobs: ['test_job']", stdout)
        mock_exit.assert_called_once_with(0)

    @patch('optimshine.optim_config.BackgroundScheduler')
    @patch('optimshine.optim_config.signal')
    def test_scheduler_setup(self, mock_signal, mock_scheduler_cls):
        mock_scheduler = MagicMock()
        mock_scheduler_cls.return_value = mock_scheduler

        cl = OptimConfig()
        cl.scheduler_setup()

        self.assertEqual(cl.running_jobs, set())
        self.assertEqual(cl.missed_jobs, set())

        expected_calls = [
            call(cl._job_running_listener, EVENT_JOB_SUBMITTED),
            call(cl._job_missed_listener, EVENT_JOB_MISSED),
            call(cl._job_finished_listener, EVENT_JOB_EXECUTED),
            call(cl._job_error_listener, EVENT_JOB_ERROR),
        ]

        mock_scheduler.add_listener.assert_has_calls(expected_calls,
                                                     any_order=True)
        mock_signal.assert_any_call(SIGINT, cl._signal_handler)
        mock_signal.assert_any_call(SIGTERM, cl._signal_handler)

    def test_scheduler_list_jobs_no_scheduler(self):
        cl = OptimConfig()
        cl.logger_setup()
        stdio = io.StringIO()
        handler = logging.StreamHandler(stream=stdio)
        cl.log.addHandler(handler)
        cl.scheduler_list_jobs()

        stdout = stdio.getvalue()
        cl.log.handlers.clear()

        self.assertIn("Scheduler not initialized", stdout)

    def test_scheduler_list_jobs_no_jobs(self):
        cl = OptimConfig()
        cl.scheduler = MagicMock()
        cl.scheduler.get_jobs.return_value = []
        cl.logger_setup()
        stdio = io.StringIO()
        handler = logging.StreamHandler(stream=stdio)
        cl.log.addHandler(handler)
        cl.scheduler_list_jobs()

        stdout = stdio.getvalue()
        cl.log.handlers.clear()

        self.assertIn("No scheduled jobs", stdout)

    def test_scheduler_list_jobs_pass(self):
        job1 = Mock()
        job1.id = "test_job_1"
        job1.next_run_time = "test_time"

        job2 = Mock()
        job2.id = "test_job_2"
        job2.next_run_time = "test_time"

        cl = OptimConfig()
        cl.scheduler = MagicMock()
        cl.scheduler.get_jobs.return_value = [job1, job2]
        cl.logger_setup()
        stdio = io.StringIO()
        handler = logging.StreamHandler(stream=stdio)
        cl.log.addHandler(handler)
        cl.scheduler_list_jobs()

        stdout = stdio.getvalue()
        cl.log.handlers.clear()

        self.assertIn("Job ID: test_job_1, Next run: test_time", stdout)
        self.assertIn("Job ID: test_job_2, Next run: test_time", stdout)


if __name__ == "__main__":
    unittest.main()
