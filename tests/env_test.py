import os
import sys

from . import TestBase

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from ssm_cache.env import EnvironmentParameterStore

class TestEnvironmentParameterStore(TestBase):
    def test_invalid_parameters(self):
        store = EnvironmentParameterStore("___TEST_PREFIX___")

        values, invalid_names = store.parameters(["test"], False)

        self.assertEquals(0, len(values))
        self.assertEquals(1, len(invalid_names))
        self.assertEquals("test", invalid_names[0])

    def test_valid_parameters(self):
        os.environ["___TEST_PREFIX___TEST"] = "exists"
        store = EnvironmentParameterStore("___TEST_PREFIX___")

        values, invalid_names = store.parameters(["test"], False)

        self.assertEquals(1, len(values))
        self.assertEquals(0, len(invalid_names))
        self.assertEquals("exists", values["test"])
