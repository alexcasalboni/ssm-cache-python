""" Test decorator utility """
import os
import sys
import mock
from . import TestBase

from ssm_cache import SSMParameter, SSMParameterGroup

class MySpecialError(Exception):
    """ Just for testing """

class TestSSMCacheDecorator(TestBase):
    """ Test Refreshable.refresh_on_error decorator """

    def setUp(self):
        """ Create params/groups for each test """
        names = ["my_param", "my_grouped_param"]
        self._create_params(names)
        self.cache = SSMParameter("my_param")
        self.group = SSMParameterGroup()
        self.grouped_param = self.group.parameter("my_grouped_param")

    def test_decorator_simple(self):
        """ Test that retry is performed on error """
        @self.cache.refresh_on_error()
        def my_function(is_retry=False):
            """ Raise error until retry """
            if not is_retry:
                raise Exception("raising an error")
            else:
                return "OK"

        self.assertEqual("OK", my_function())

    def test_decorator_grouped_simple(self):
        """ Test that retry is performed on error for groups """
        @self.group.refresh_on_error()
        def my_function(is_retry=False):
            """ Raise error until retry """
            if not is_retry:
                raise Exception("raising an error")
            else:
                return "OK"

        self.assertEqual("OK", my_function())

    def test_decorator_error_class(self):
        """ Special error is handled, if given """
        @self.cache.refresh_on_error(MySpecialError)
        def my_function(is_retry=False):
            """ Raise error until retry """
            if not is_retry:
                raise MySpecialError("raising a special error")
            else:
                return "OK"

        self.assertEqual("OK", my_function())

    def test_decorator_error_generic(self):
        """ Generic errors are not handled, if error_class is given """
        @self.cache.refresh_on_error(MySpecialError)
        def my_function(is_retry=False):
            """ Raise error until retry """
            if not is_retry:
                raise Exception("raising a regular error")
            else:
                return "OK"

        with self.assertRaises(Exception):
            my_function()

    def test_decorator_callback(self):
        """ Callback is invoked on error, if provided """

        callback = mock.Mock()

        @self.cache.refresh_on_error(Exception, callback)
        def my_function(is_retry=False):
            """ Raise error until retry """
            if not is_retry:
                raise Exception("raising a regular error")
            else:
                return "OK"

        self.assertEqual("OK", my_function())
        self.assertEqual(1, callback.call_count)

    def test_decorator_callback_invalid(self):
        """ Error if non-collable callback """

        with self.assertRaises(TypeError):
            @self.cache.refresh_on_error(Exception, "invalid_callable")
            def my_function():
                """ this function won't ever get called! """

        try:
            my_function()
        except NameError:
            pass  # ok, the function doesn't exist!

    def test_decorator_retry_argument(self):
        """ Retry argument can be customized """

        @self.cache.refresh_on_error(retry_argument='my_retry_name')
        def my_function(my_retry_name=False):
            """ Raise error until retry """
            if not my_retry_name:
                raise Exception("raising a regular error")
            else:
                return "OK"

        self.assertEqual("OK", my_function())

    def test_decorator_recursion(self):
        """ Only the first exception is handled """

        @self.cache.refresh_on_error()
        def my_function(is_retry=False):
            """ Always raise an exception with True/False as message """
            raise Exception("%s" % is_retry)

        with self.assertRaises(Exception) as context_manager:
            my_function()

        self.assertEqual(str(context_manager.exception), "True")

    def test_decorator_all_together(self):
        """ All the decorator features should work together """

        data = {
            "result": "KO",
        }

        def callback():
            """ The callback will be invoked before re-trying """
            data['result'] = "OK"

        @self.cache.refresh_on_error(MySpecialError, callback, retry_argument="my_retry_name")
        def my_function(my_retry_name=False):
            """ Raise error until retry (with custom name) """
            if not my_retry_name:
                raise MySpecialError("raising a special error")
            else:
                return data['result']

        self.assertEqual("OK", my_function())
