import os
import sys

from . import TestBase

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from ssm_cache.env import EnvironmentParameterStore
from ssm_cache.chain import ChainedParameterStore

class AlternativeStore(object):
    @classmethod
    def parameters(cls, names, with_decryption):
        return {names[0]: "alternative"}, []

class TestChainedParameterStore(TestBase):
    def test(self):
        store = ChainedParameterStore(stores=[EnvironmentParameterStore("___TEST_PREFIX__"), AlternativeStore])

        values, invalid_names = store.parameters(["test"], False)

        self.assertEquals(0, len(invalid_names))
        self.assertEquals("alternative", values["test"])
