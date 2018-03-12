""" Define a test base class for all tests """
import unittest
import boto3


class TestBase(unittest.TestCase):
    """ Base class with mock values and boto3 client """

    PARAM_VALUE = "abc123"
    PARAM_LIST_COUNT = 2
    ssm_client = boto3.client('ssm')

    def _create_params(self, names, value=PARAM_VALUE, parameter_type="String"):
        if parameter_type == 'StringList' and not isinstance(value, list):
            value = ",".join([value] * self.PARAM_LIST_COUNT)
        for name in names:
            self.ssm_client.put_parameter(
                Name=name,
                Value=value,
                Type=parameter_type,
                Overwrite=True,
            )
