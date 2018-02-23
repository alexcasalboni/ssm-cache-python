
import os
import sys

from . import TestBase

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from ssm_cache.store import ParameterStore

class TestParameterStore(TestBase):
    def test_not_implemented(self):
        try:
            ParameterStore.parameters([], False)
            self.assertEqual("expected exception", "did not get one")
        except NotImplementedError:
            pass
