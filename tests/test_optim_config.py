import unittest
import os

from logging import RootLogger
from optimshine.optim_config import OptimConfig


class TestOptimConfig(unittest.TestCase):
    def test_loger_setup(self):
        cl = OptimConfig()
        cl.logger_setup()
        self.assertTrue(isinstance(cl.log, RootLogger),
                        msg=f"Log type is wrong ({type(cl.log).__name__})")

    def test_envs_setup_no_logger(self):
        cl = OptimConfig()
        result = cl.envs_setup()
        self.assertFalse(result)

    def test_envs_setup_wrong_envpath(self):
        cl = OptimConfig()
        cl.logger_setup()
        result = cl.envs_setup("wrong")
        self.assertFalse(result)
        self

    def test_envs_setup_pass(self):
        cl = OptimConfig()
        cl.logger_setup()
        result = cl.envs_setup("tests/.testenv")
        self.assertTrue(result)
        testvar = os.getenv("TESTVAR")
        self.assertEqual(testvar, "test")


if __name__ == "__main__":
    unittest.main()
