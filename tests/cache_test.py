""" Test ssm_cache/cache.py main functionalities """
from __future__ import print_function
import os
import sys
from datetime import datetime, timedelta
from moto import mock_ssm
from . import TestBase

# pylint: disable=wrong-import-order,wrong-import-position

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from ssm_cache import SSMParameter, SSMParameterGroup, InvalidParameterError
from ssm_cache.cache import Refreshable


# pylint: disable=protected-access
@mock_ssm
class TestSSMCache(TestBase):
    """ SSMParameter and SSMParameterGroup tests """

    def setUp(self):
        names = ["my_param", "my_param_1", "my_param_2", "my_param_3"]
        self._create_params(names)

    def test_creation(self):
        """ Test regular creation """
        # single string
        param = SSMParameter("my_param")
        self.assertTrue(param._with_decryption)
        self.assertIsNone(param._max_age)
        self.assertIsNone(param._last_refresh_time)
        # invalid params
        with self.assertRaises(TypeError):
            SSMParameter()  # pylint: disable=no-value-for-parameter
        with self.assertRaises(ValueError):
            SSMParameter(None)

        group = SSMParameterGroup()
        param = group.parameter("my_param")
        with self.assertRaises(TypeError):
            group.parameter()  # pylint: disable=no-value-for-parameter

    def test_should_refresh(self):
        """ Unit test _should_refresh private method """
        # without max age
        ref = Refreshable(None)
        self.assertFalse(ref._should_refresh())
        # with max age and no data
        ref = Refreshable(max_age=10)
        self.assertTrue(ref._should_refresh())
        # with max age and last refreshed date OK
        ref._last_refresh_time = datetime.utcnow()
        self.assertFalse(ref._should_refresh())
        # with max age and last refreshed date KO
        ref._last_refresh_time = datetime.utcnow() - timedelta(seconds=20)
        self.assertTrue(ref._should_refresh())

    def test_refreshable_abstract(self):
        """ Test NotImplementedError on abstract class """
        ref = Refreshable(None)
        with self.assertRaises(NotImplementedError):
            ref.refresh()

    def test_simple(self):
        """ Test simple parameter case """
        cache = SSMParameter("my_param")
        my_value = cache.value
        self.assertEqual(my_value, self.PARAM_VALUE)

    def test_unexisting(self):
        """ Test unexisting parameter case """
        cache = SSMParameter("my_param_invalid_name")
        with self.assertRaises(InvalidParameterError):
            print(cache.value)

    def test_unexisting_in_group(self):
        """ Test unexisting parameter in group case """
        group = SSMParameterGroup()
        _ = group.parameter("my_param_1")
        __ = group.parameter("my_param_unexisting")
        with self.assertRaises(InvalidParameterError):
            group.refresh()


    def test_with_expiration(self):
        """ Test simple case with expiration """
        cache = SSMParameter("my_param", max_age=300)  # 5 minutes expiration time
        my_value = cache.value
        self.assertEqual(my_value, self.PARAM_VALUE)

    def test_main_with_expiration_group(self):
        """ Test group case with expiration """
        group = SSMParameterGroup(max_age=300)
        param_1 = group.parameter("my_param_1")
        param_2 = group.parameter("my_param_2")
        param_3 = group.parameter("my_param_3")

        # individual params don't share max_age internally (for now)
        for param in (param_1, param_2, param_3):
            self.assertEqual(param._max_age, None)

        # force fetch
        group.refresh()

        # pretend time has passed (for the group)
        group._last_refresh_time = datetime.utcnow() - timedelta(seconds=301)
        self.assertTrue(group._should_refresh())
        self.assertTrue(param_1._should_refresh())
        self.assertTrue(param_2._should_refresh())
        self.assertTrue(param_3._should_refresh())

    def test_without_encryption(self):
        """ Test simple case without encryption """
        param = SSMParameter("my_param", with_decryption=False)
        self.assertEqual(param.value, self.PARAM_VALUE)

    def test_with_param_group(self):
        """ Test simple group case """
        group = SSMParameterGroup()
        param_1 = group.parameter("my_param_1")
        param_2 = group.parameter("my_param_2")
        param_3 = group.parameter("my_param_3")
        # one by one
        my_value_1 = param_1.value
        my_value_2 = param_2.value
        my_value_3 = param_3.value
        self.assertEqual(my_value_1, self.PARAM_VALUE)
        self.assertEqual(my_value_2, self.PARAM_VALUE)
        self.assertEqual(my_value_3, self.PARAM_VALUE)

    def test_group_same_name(self):
        """ Test group with duplicated name case """
        group = SSMParameterGroup()
        _ = group.parameter("my_param_1")
        __ = group.parameter("my_param_1")
        self.assertEqual(1, len(group))

    def test_main_with_explicit_refresh(self):
        """ Test explicit refresh case """
        param = SSMParameter("my_param")  # will not expire

        class InvalidCredentials(Exception):
            """ Mock exception class """

        def do_something():
            """ Raise an exception until the value has changed """
            my_value = param.value
            if my_value == self.PARAM_VALUE:
                raise InvalidCredentials()

        try:
            do_something()
        except InvalidCredentials:
            # manually update value
            self._create_params(["my_param"], "new_value")
            param.refresh()  # force refresh
            do_something()  # won't fail anymore

    def test_explicit_group_refresh(self):
        """ Test group refresh case """
        group = SSMParameterGroup()  # will not expire
        param_1 = group.parameter("my_param_1")
        param_2 = group.parameter("my_param_2")

        class InvalidCredentials(Exception):
            """ Mock exception class """

        def do_something():
            """ Raise an exception until the value has changed """
            my_value = param_1.value
            if my_value == self.PARAM_VALUE:
                raise InvalidCredentials()

        try:
            do_something()
        except InvalidCredentials:
            # manually update value
            new_value = "new_value"
            self._create_params(["my_param_1", "my_param_2"], new_value)
            group.refresh()  # force refresh
            do_something()  # won't fail anymore
            self.assertEqual(param_2.value, new_value)

    def test_explicit_refresh_param(self):
        """ Test group refresh on param case """
        group = SSMParameterGroup()  # will not expire
        param_1 = group.parameter("my_param_1")
        param_2 = group.parameter("my_param_2")

        class InvalidCredentials(Exception):
            """ Mock exception class """

        def do_something():
            """ Raise an exception until the value has changed """
            my_value = param_1.value
            if my_value == self.PARAM_VALUE:
                raise InvalidCredentials()

        try:
            do_something()
        except InvalidCredentials:
            # manually update value
            new_value = "new_value"
            self._create_params(["my_param_1", "my_param_2"], new_value)
            param_1.refresh()  # force refresh
            do_something()  # won't fail anymore
            self.assertEqual(param_2.value, new_value)

    def test_main_lambda_handler(self):
        """ Test simple AWS Lambda handler """
        cache = SSMParameter("my_param")

        def lambda_handler(event, context):
            """ Simple Lambda handler that just prints a string """
            print(event, context)
            secret_value = cache.value
            return 'Hello from Lambda with secret %s' % secret_value

        return_value = lambda_handler(None, None)
        expected_value = 'Hello from Lambda with secret %s' % self.PARAM_VALUE
        self.assertEqual(return_value, expected_value)
