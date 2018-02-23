"""Parameter store that reads from the provided set of backing stores."""
from __future__ import absolute_import, print_function

from .store import ParameterStore
from .env import EnvironmentParameterStore
from .ssm import SSMParameterStore

class ChainedParameterStore(ParameterStore): # pylint: disable=too-few-public-methods
    """Concrete ParameterStore that reads from the provided set of backing stores."""

    def __init__(self, stores=None):
        if stores is None:
            self._stores = [EnvironmentParameterStore(), SSMParameterStore()]
        else:
            self._stores = stores

    def parameters(self, names, with_decryption):
        """Retrieve the named parameters from the chain of stores. """
        values = {}
        invalid_names = names

        for store in self._stores:
            cur_values, invalid_names = store.parameters(invalid_names, with_decryption)
            values.update(cur_values)

            if not invalid_names:
                break

        return values, invalid_names
