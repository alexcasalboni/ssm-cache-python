import os
import sys
from datetime import datetime, timedelta
import boto3
from moto import mock_ssm
from . import TestBase

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from ssm_cache import SSMParameter, InvalidParam

@mock_ssm
class TestSSMCache(TestBase):

    def setUp(self):
        names = ["my_param", "my_param_1", "my_param_2", "my_param_3"]
        self._create_params(names)

    def test_creation(self):
        # single string
        cache = SSMParameter("my_param")
        self.assertEqual(1, len(cache._names))
        self.assertTrue(cache._with_decryption)
        self.assertIsNone(cache._max_age)
        self.assertIsNone(cache._last_refresh_time)
        # list of params
        cache = SSMParameter(["my_param_1", "my_param_2"])
        self.assertEqual(2, len(cache._names))
        # invalid params
        with self.assertRaises(ValueError):
            SSMParameter()
        with self.assertRaises(ValueError):
            SSMParameter(None)
        with self.assertRaises(ValueError):
            SSMParameter([])

    def test_should_refresh(self):
        # without max age
        cache = SSMParameter("my_param")
        self.assertFalse(cache._should_refresh())
        # with max age and no data
        cache = SSMParameter("my_param", max_age=10)
        self.assertTrue(cache._should_refresh())
        # with max age and last refreshed date OK
        cache._last_refresh_time = datetime.utcnow()
        self.assertFalse(cache._should_refresh())
        # with max age and last refreshed date KO
        cache._last_refresh_time = datetime.utcnow() - timedelta(seconds=20)
        self.assertTrue(cache._should_refresh())

    def test_main(self):
        cache = SSMParameter("my_param")
        my_value = cache.value()
        self.assertEqual(my_value, self.PARAM_VALUE)

    def test_unexisting(self):
        cache = SSMParameter("my_param_invalid_name")
        with self.assertRaises(InvalidParam):
            cache.value()

    def test_not_configured(self):
        cache = SSMParameter(["param_1", "param_2"])
        with self.assertRaises(InvalidParam):
            cache.value("param_3")

    def test_main_with_expiration(self):
        cache = SSMParameter("my_param", max_age=300)  # 5 minutes expiration time
        my_value = cache.value()
        self.assertEqual(my_value, self.PARAM_VALUE)


    def test_main_without_encryption(self):
        cache = SSMParameter("my_param", with_decryption=False)
        my_value = cache.value()
        self.assertEqual(my_value, self.PARAM_VALUE)

    def test_main_with_multiple_params(self):
        cache = SSMParameter(["my_param_1", "my_param_2", "my_param_3"])
        # one by one
        my_value_1 = cache.value("my_param_1")
        my_value_2 = cache.value("my_param_2")
        my_value_3 = cache.value("my_param_3")
        self.assertEqual(my_value_1, self.PARAM_VALUE)
        self.assertEqual(my_value_2, self.PARAM_VALUE)
        self.assertEqual(my_value_3, self.PARAM_VALUE)
        with self.assertRaises(TypeError):
            cache.value()  # name is required
        # or all together
        my_value_1, my_value_2, my_value_3 = cache.values()
        self.assertEqual(my_value_1, self.PARAM_VALUE)
        self.assertEqual(my_value_2, self.PARAM_VALUE)
        self.assertEqual(my_value_3, self.PARAM_VALUE)
        # or a subset
        my_value_1, my_value_2 = cache.values(["my_param_1", "my_param_2"])
        self.assertEqual(my_value_1, self.PARAM_VALUE)
        self.assertEqual(my_value_2, self.PARAM_VALUE)

    def test_main_with_explicit_refresh(self):
        cache = SSMParameter("my_param")  # will not expire

        class InvalidCredentials(Exception):
            pass

        def do_something():
            my_value = cache.value()
            if my_value == self.PARAM_VALUE:
                raise InvalidCredentials()

        try:
            do_something()
        except InvalidCredentials:
            # manually update value
            self._create_params(["my_param"], "new_value")
            cache.refresh()  # force refresh
            do_something()  # won't fail anymore

    def test_main_lambda_handler(self):
        cache = SSMParameter("my_param")

        def lambda_handler(event, context):
            secret_value = cache.value()
            return 'Hello from Lambda with secret %s' % secret_value
        
        lambda_handler(None, None)
