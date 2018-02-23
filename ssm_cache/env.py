"""Parameter store that reads from the environment"""
from __future__ import absolute_import, print_function

import os

from .store import ParameterStore

class EnvironmentParameterStore(ParameterStore): # pylint: disable=too-few-public-methods
    """Concrete ParameterStore that reads from OS environment variables."""

    def __init__(self, prefix=None):
        self._prefix = "" if prefix is None else prefix

    def parameters(self, names, with_decryption):
        """Retrieve the named parameters from OS environment variables."""
        values = {}
        invalid_names = []
        for name in names:
            prefixed_name = (self._prefix + name).upper()

            if prefixed_name in os.environ:
                values[name] = os.environ[prefixed_name]
            else:
                invalid_names.append(name)

        return values, invalid_names
