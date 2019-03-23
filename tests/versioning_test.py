""" Test ssm_cache/cache.py main functionalities """
from __future__ import print_function
import unittest
import os
import sys
import placebo
import boto3

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ssm_cache import (
    SSMParameter,
    SSMParameterGroup,
    InvalidParameterError,
    InvalidVersionError,
)
from ssm_cache.cache import Refreshable


# pylint: disable=protected-access
class TestSSMVersioning(unittest.TestCase):
    """ SSMParameter versioning tests """

    PARAM_VALUE = "abc123"
    PARAM_VALUE_V2 = "789xyz"

    PLACEBO_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), 'placebo/versioning'))
    
    @classmethod
    def tearDownClass(cls):
        # pylint: disable=protected-access
        # reset class-level client for other tests
        SSMParameter._ssm_client = None
        SSMParameterGroup._ssm_client = None

    def _setUp(self, subfolder):
        session = boto3.Session()
        pill = placebo.attach(session, data_path=os.path.join(self.PLACEBO_PATH, subfolder))
        pill.playback()
        self.ssm_client = session.client('ssm')
        SSMParameter.set_ssm_client(self.ssm_client)

    def _create_or_update_param(self, name, value=PARAM_VALUE):
        arguments = dict(
            Name=name,
            Value=value,
            Type="String",
            Overwrite=True,
        )
        self.ssm_client.put_parameter(**arguments)

    def _delete_param(self, name):
        arguments = dict(
            Name=name,
        )
        self.ssm_client.delete_parameter(**arguments)


    def test_update_versions(self):
        """ Test version update """

        method_name = sys._getframe().f_code.co_name
        self._setUp(method_name)

        name = method_name
        self._create_or_update_param(name)

        param = SSMParameter(name)

        self.assertEqual(param.version, 1)
        self.assertEqual(param.value, self.PARAM_VALUE)

        # this will update the value and create version 2
        self._create_or_update_param(name, self.PARAM_VALUE_V2)

        param.refresh()

        # refreshing should give you version 2
        self.assertEqual(param.version, 2)
        self.assertEqual(param.value, self.PARAM_VALUE_V2)

        self._delete_param(name)


    def test_select_versions(self):
        """ Test version selection """

        method_name = sys._getframe().f_code.co_name
        self._setUp(method_name)

        name = method_name
        self._create_or_update_param(name)

        param = SSMParameter("%s:1" % name)

        self.assertEqual(param.value, self.PARAM_VALUE)
        self.assertEqual(param.version, 1)

        # this will update the value and create version 2
        self._create_or_update_param(name, self.PARAM_VALUE_V2)

        param.refresh()

        self.assertEqual(param.value, self.PARAM_VALUE)
        self.assertEqual(param.version, 1)

        self._delete_param(name)
        

    def test_versions_unexisting(self):
        """ Test non existing version """
        method_name = sys._getframe().f_code.co_name
        self._setUp(method_name)

        name = method_name
        self._create_or_update_param(name)

        param = SSMParameter("%s:10" % name)

        with self.assertRaises(InvalidParameterError):
            print(param.value)

        self._delete_param(name)

    def test_versions_invalid(self):
        """ Test invalid version """

        name = "my_param"
        
        with self.assertRaises(InvalidVersionError):
            SSMParameter("%s:hello" % name)

        with self.assertRaises(InvalidVersionError):
            SSMParameter("%s:0" % name)

        with self.assertRaises(InvalidVersionError):
            SSMParameter("%s:-1" % name)

        with self.assertRaises(InvalidVersionError):
            SSMParameter("%s:" % name)

    def test_versions_group(self):
        """ Test version update in a group """
        method_name = sys._getframe().f_code.co_name
        self._setUp(method_name)

        name = method_name
        self._create_or_update_param(name)

        group = SSMParameterGroup()
        param = group.parameter(name)

        self.assertEqual(param.version, 1)
        self.assertEqual(param.value, self.PARAM_VALUE)

        # this will update the value and create version 2
        self._create_or_update_param(name, self.PARAM_VALUE_V2)

        group.refresh()

        # refreshing should give you version 2
        self.assertEqual(param.version, 2)
        self.assertEqual(param.value, self.PARAM_VALUE_V2)

        self._delete_param(name)


    def test_versions_group_select(self):
        """ Test version selection in a group """
        method_name = sys._getframe().f_code.co_name
        self._setUp(method_name)

        name = method_name
        self._create_or_update_param(name)

        # this will update the value and create version 2
        self._create_or_update_param(name, self.PARAM_VALUE_V2)

        group = SSMParameterGroup()
        param = group.parameter("%s:1" % name)

        self.assertEqual(param.version, 1)
        self.assertEqual(param.value, self.PARAM_VALUE)

        self._delete_param(name)
