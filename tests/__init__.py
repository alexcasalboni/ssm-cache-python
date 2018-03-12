""" Define a test base class for all tests """
import unittest
import boto3


class TestBase(unittest.TestCase):
    """ Base class with mock values and boto3 client """

    PARAM_VALUE = "abc123"
    ssm_client = boto3.client('ssm')

    def _create_params(self, names, value=PARAM_VALUE):
        for name in names:
            self.ssm_client.put_parameter(
                Name=name,
                Value=value,
                Type="String",
                Overwrite=True,
            )
