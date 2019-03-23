""" Define a test base class for all tests """
import unittest
import os
import sys
import logging
from moto import mock_ssm, mock_secretsmanager
import boto3
import botocore

# directly from here: https://github.com/boto/boto3/issues/521
logging.getLogger('boto3').setLevel(logging.CRITICAL)
logging.getLogger('botocore').setLevel(logging.CRITICAL)

# pylint: disable=wrong-import-order,wrong-import-position
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ssm_cache import SSMParameter, SSMParameterGroup

@mock_ssm
@mock_secretsmanager
class TestBase(unittest.TestCase):
    """ Base class with mock values and boto3 client """

    PARAM_VALUE = "abc123"
    PARAM_LIST_COUNT = 2
    ssm_client = boto3.client('ssm')
    secretsmanager_client = boto3.client('secretsmanager')

    @classmethod
    def tearDownClass(cls):
        # pylint: disable=protected-access
        # reset class-level client for other tests
        SSMParameter._ssm_client = None
        SSMParameterGroup._ssm_client = None

    def _create_params(self, names, value=PARAM_VALUE, parameter_type="String"):
        if parameter_type == 'StringList' and not isinstance(value, list):
            value = ",".join([value] * self.PARAM_LIST_COUNT)
        for name in names:
            arguments = dict(
                Name=name,
                Value=value,
                Type=parameter_type,
                Overwrite=True,
            )
            if parameter_type == 'SecureString':
                arguments['KeyId'] = 'alias/aws/ssm'
            self.ssm_client.put_parameter(**arguments)

    def _create_secrets(self, names, value=PARAM_VALUE, parameter_type="SecretString"):
        for name in names:
            arguments = dict(
                Name=name,
                Description=name,
            )
            if parameter_type == 'SecretString':
                arguments['SecretString'] = value
            if parameter_type == 'SecretBinary':
                arguments['SecretBinary'] = value
            
            try:
                #self.secretsmanager_client.describe_secret(SecretId=name)
                self.secretsmanager_client.create_secret(**arguments)
            except self.secretsmanager_client.exceptions.ResourceExistsException as ex:
                print("Secret already exists")
