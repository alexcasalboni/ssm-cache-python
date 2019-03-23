""" Test ssm_cache/cache.py main functionalities """
from __future__ import print_function
from moto import mock_ssm, mock_secretsmanager
from . import TestBase

from ssm_cache import SSMParameterGroup, SecretsManagerParameter, InvalidParameterError


# pylint: disable=protected-access
@mock_ssm
@mock_secretsmanager
class TestSSMSecrets(TestBase):
    """ SecretsManagerParameter tests """

    def setUp(self):
        names = ["my_secret_param", "my_secret_param_1", "my_secret_param_2", "my_secret_param_3"]
        self._create_secrets(names)

    def test_creation(self):
        """ Test regular creation """
        # single string
        param = SecretsManagerParameter("my_secret")
        self.assertTrue(param._with_decryption)
        self.assertIsNone(param._max_age)
        self.assertIsNone(param._last_refresh_time)
        self.assertTrue(param._name.startswith(SecretsManagerParameter.PREFIX))
        # invalid params
        with self.assertRaises(TypeError):
            SecretsManagerParameter()  # pylint: disable=no-value-for-parameter
        with self.assertRaises(ValueError):
            SecretsManagerParameter(None)
        with self.assertRaises(InvalidParameterError):
            SecretsManagerParameter("/my_secret")

        group = SSMParameterGroup()
        secret = group.secret("my_secret")
        with self.assertRaises(TypeError):
            group.secret()  # pylint: disable=no-value-for-parameter
        with self.assertRaises(InvalidParameterError):
            group.secret("/my_secret")

    def test_unexisting(self):
        """ Test unexisting parameter case """
        param = SecretsManagerParameter("my_secret_invalid_name")
        with self.assertRaises(InvalidParameterError):
            print(param.value)

    def test_unexisting_in_group(self):
        """ Test unexisting parameter in group case """
        group = SSMParameterGroup()
        _ = group.secret("my_secret_1")
        __ = group.secret("my_secret_unexisting")
        with self.assertRaises(InvalidParameterError):
            group.refresh()

    def test_group_same_name(self):
        """ Test group with duplicated name case """
        group = SSMParameterGroup()
        param = group.secret("my_secret_1")
        __ = group.secret("my_secret_1")
        self.assertEqual(1, len(group))
        # self.assertEqual(param.value, self.PARAM_VALUE)

    def test_with_explicit_refresh(self):
        """ Test explicit refresh case """
        param = SecretsManagerParameter("my_secret")  # will not expire

        class InvalidCredentials(Exception):
            """ Mock exception class """

        def do_something():
            """ Raise an exception until the value has changed """
            my_value = param.value
            if my_value == self.PARAM_VALUE:
                raise InvalidCredentials()

        # try:
        #     do_something()
        # except InvalidCredentials:
        #     # manually update value
        #     self.secretsmanager_client.put_secret_value(SecretId="my_secret", SecretString="new_value")
        #     param.refresh()  # force refresh
        #     do_something()  # won't fail anymore
        #     self.secretsmanager_client.put_secret_value(SecretId="my_secret", SecretString=self.PARAM_VALUE)  # reset
