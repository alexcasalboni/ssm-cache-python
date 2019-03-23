""" Test boto3 client ovverride """
import unittest
import os
import sys
from moto import mock_ssm
import boto3
import placebo
from . import TestBase

from ssm_cache import SSMParameter, SSMParameterGroup

class TestClientOverride(unittest.TestCase):
    """ Refreshable.set_ssm_client tests """

    PARAM_VALUE = "abc123"
    PLACEBO_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), 'placebo/override'))

    def test_with_placebo(self):
        """ Test that set_ssm_client works fine with Placebo """
        session = boto3.Session()
        pill = placebo.attach(session, data_path=self.PLACEBO_PATH)
        pill.playback()

        client = session.client('ssm')

        SSMParameter.set_ssm_client(client)

        param = SSMParameter("my_param")
        self.assertEqual(param.value, self.PARAM_VALUE)


    def test_with_illegal_client(self):
        """ Test invalid client (without required methods) """
        with self.assertRaises(TypeError):
            SSMParameter.set_ssm_client(42)

        # pylint: disable=too-few-public-methods
        class MyInvalidClient(object):
            """ This client only has get_parameters """
            def get_parameters(self):
                """ Empty method """

        with self.assertRaises(TypeError):
            client = MyInvalidClient()
            SSMParameter.set_ssm_client(client)

    @mock_ssm
    def test_with_valid_client(self):
        """ Test invalid client (without required methods) """
        # pylint: disable=unused-argument,no-self-use
        class MyValidClient(object):
            """ This client has all the required methods """
            def get_parameters(self, *args, **kwargs):
                """ Mock method """
                return {
                    'InvalidParameters': [],
                    'Parameters': [
                        {
                            "Type": "String",
                            "Name": "my_param",
                            "Value": "abc123",
                            "Version": 1
                        },
                    ],
                }
            def get_parameters_by_path(self, *args, **kwargs):
                """ Mock method """
                return {
                    "Parameters": [
                        {
                            "Type": "String",
                            "Name": "/foo/bar/1",
                            "Value": "abc123",
                            "Version": 1
                        },
                        {
                            "Type": "String",
                            "Name": "/foo/bar/2",
                            "Value": "abc123",
                            "Version": 1
                        },
                    ]
                }

        client = MyValidClient()
        SSMParameter.set_ssm_client(client)

        param = SSMParameter("my_param")
        self.assertEqual(param.value, self.PARAM_VALUE)

        group = SSMParameterGroup()
        param = group.parameter("my_param")
        self.assertEqual(param.value, self.PARAM_VALUE)

        params = group.parameters("/foo/bar/")
        self.assertEqual(len(params), 2)
        for param in params:
            self.assertEqual(param.value, self.PARAM_VALUE)
