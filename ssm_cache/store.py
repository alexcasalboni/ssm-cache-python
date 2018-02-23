""" Generic parameter store abstract class """
from __future__ import absolute_import, print_function

class ParameterStore(object): # pylint: disable=too-few-public-methods
    """ Abstract class for parameter stores """
    @classmethod
    def parameters(cls, names, with_decryption):
        """ Get the named parameters from the store """
        raise NotImplementedError
