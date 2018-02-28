import os
import sys
from datetime import datetime, timedelta
import boto3
from moto import mock_ssm
from . import TestBase

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from ssm_cache import SSMParameter, SSMParameterGroup, InvalidParameterError
from ssm_cache.cache import Refreshable

@mock_ssm
class TestSSMCache(TestBase):

    def setUp(self):
        names = ["my_param", "my_param_1", "my_param_2", "my_param_3"]
        self._create_params(names)

    def test_creation(self):
        # single string
        cache = SSMParameter("my_param")
        self.assertTrue(cache._with_decryption)
        self.assertIsNone(cache._max_age)
        self.assertIsNone(cache._last_refresh_time)
        # invalid params
        with self.assertRaises(TypeError):
            SSMParameter()
        with self.assertRaises(ValueError):
            SSMParameter(None)
        
        group = SSMParameterGroup()
        parameter = group.parameter("my_param")
        with self.assertRaises(TypeError):
            group.parameter()

    def test_should_refresh(self):
        # without max age
        cache = Refreshable(None)
        self.assertFalse(cache._should_refresh())
        # with max age and no data
        cache = Refreshable(max_age=10)
        self.assertTrue(cache._should_refresh())
        # with max age and last refreshed date OK
        cache._last_refresh_time = datetime.utcnow()
        self.assertFalse(cache._should_refresh())
        # with max age and last refreshed date KO
        cache._last_refresh_time = datetime.utcnow() - timedelta(seconds=20)
        self.assertTrue(cache._should_refresh())

    def test_refreshable_abstract(self):
        cache = Refreshable(None)
        with self.assertRaises(NotImplementedError):
            cache.refresh()

    def test_main(self):
        cache = SSMParameter("my_param")
        my_value = cache.value
        self.assertEqual(my_value, self.PARAM_VALUE)

    def test_unexisting(self):
        cache = SSMParameter("my_param_invalid_name")
        with self.assertRaises(InvalidParameterError):
            cache.value

    def test_unexisting_in_group(self):
        group = SSMParameterGroup()
        param_1 = group.parameter("my_param_1")
        param_2 = group.parameter("my_param_unexisting")
        with self.assertRaises(InvalidParameterError):
            group.refresh()


    def test_main_with_expiration(self):
        cache = SSMParameter("my_param", max_age=300)  # 5 minutes expiration time
        my_value = cache.value
        self.assertEqual(my_value, self.PARAM_VALUE)

    def test_main_with_expiration_group(self):
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

    def test_main_without_encryption(self):
        cache = SSMParameter("my_param", with_decryption=False)
        my_value = cache.value
        self.assertEqual(my_value, self.PARAM_VALUE)

    def test_main_with_param_group(self):
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
        group = SSMParameterGroup()
        param_1 = group.parameter("my_param_1")
        param_1_again = group.parameter("my_param_1")
        self.assertEqual(1, len(group))

    def test_main_with_explicit_refresh(self):
        cache = SSMParameter("my_param")  # will not expire

        class InvalidCredentials(Exception):
            pass

        def do_something():
            my_value = cache.value
            if my_value == self.PARAM_VALUE:
                raise InvalidCredentials()

        try:
            do_something()
        except InvalidCredentials:
            # manually update value
            self._create_params(["my_param"], "new_value")
            cache.refresh()  # force refresh
            do_something()  # won't fail anymore

    def test_main_with_explicit_refresh_of_group(self):
        group = SSMParameterGroup()  # will not expire
        param_1 = group.parameter("my_param_1")
        param_2 = group.parameter("my_param_2")

        class InvalidCredentials(Exception):
            pass

        def do_something():
            my_value = param_1.value
            if my_value == self.PARAM_VALUE:
                raise InvalidCredentials()

        try:
            do_something()
        except InvalidCredentials:
            # manually update value
            NEW_VALUE = "new_value"
            self._create_params(["my_param_1", "my_param_2"], NEW_VALUE)
            group.refresh()  # force refresh
            do_something()  # won't fail anymore
            self.assertEqual(param_2.value, NEW_VALUE)

    def test_main_with_explicit_refresh_of_group_param(self):
        group = SSMParameterGroup()  # will not expire
        param_1 = group.parameter("my_param_1")
        param_2 = group.parameter("my_param_2")

        class InvalidCredentials(Exception):
            pass

        def do_something():
            my_value = param_1.value
            if my_value == self.PARAM_VALUE:
                raise InvalidCredentials()

        try:
            do_something()
        except InvalidCredentials:
            # manually update value
            NEW_VALUE = "new_value"
            self._create_params(["my_param_1", "my_param_2"], NEW_VALUE)
            param_1.refresh()  # force refresh
            do_something()  # won't fail anymore
            self.assertEqual(param_2.value, NEW_VALUE)

    def test_main_lambda_handler(self):
        cache = SSMParameter("my_param")

        def lambda_handler(event, context):
            secret_value = cache.value
            return 'Hello from Lambda with secret %s' % secret_value
        
        lambda_handler(None, None)
