""" Cache module that implements the SSM caching wrapper """
from __future__ import absolute_import, print_function

from datetime import datetime, timedelta
from functools import wraps
import six

import boto3

class InvalidParameterError(Exception):
    """ Raised when something's wrong with the provided param name """

class Refreshable(object):
    """ Abstract class for refreshable objects (with max-age) """

    ssm_client = boto3.client('ssm')

    def __init__(self, max_age):
        self._last_refresh_time = None
        self._max_age = max_age
        self._max_age_delta = timedelta(seconds=max_age or 0)

    def _refresh(self):
        raise NotImplementedError

    def _should_refresh(self):
        # never force refresh if no max_age is configured
        if not self._max_age:
            return False
        # always force refresh if values were never fetched
        if not self._last_refresh_time:
            return True
        # force refresh only if max_age seconds have expired
        return datetime.utcnow() > self._last_refresh_time + self._max_age_delta

    def refresh(self):
        """ Updates the value(s) of this refreshable """
        self._refresh()
        # keep track of update date for max_age checks
        self._last_refresh_time = datetime.utcnow()

    @classmethod
    def _get_parameters(cls, names, with_decryption):
        values = {}
        invalid_names = []
        for name_batch in _batch(names, 10): # can only get 10 parameters at a time
            response = cls.ssm_client.get_parameters(
                Names=list(name_batch),
                WithDecryption=with_decryption,
            )
            invalid_names.extend(response['InvalidParameters'])
            for item in response['Parameters']:
                values[item['Name']] = item['Value']

        return values, invalid_names

    def refresh_on_error(
            self,
            error_class=Exception,
            error_callback=None,
            retry_argument='is_retry'
        ):
        """ Decorator to handle errors and retries """
        if error_callback and not callable(error_callback):
            raise TypeError("error_callback must be callable")
        def true_decorator(func):
            """ Actual func wrapper """
            @wraps(func)
            def wrapped(*args, **kwargs):
                """ Actual error/retry handling """
                try:
                    return func(*args, **kwargs)
                except error_class:
                    self.refresh()
                    if error_callback:
                        error_callback()
                    if retry_argument:
                        kwargs[retry_argument] = True
                    return func(*args, **kwargs)
            return wrapped
        return true_decorator

class SSMParameterGroup(Refreshable):
    """ Concrete class that wraps multiple SSM Parameters """

    def __init__(self, max_age=None, with_decryption=True):
        super(SSMParameterGroup, self).__init__(max_age)

        self._with_decryption = with_decryption
        self._parameters = {}

    def parameter(self, name):
        """ Create a new SSMParameter by name (or retrieve an existing one) """
        if name in self._parameters:
            return self._parameters[name]
        parameter = SSMParameter(name)
        parameter._group = self  # pylint: disable=protected-access
        self._parameters[name] = parameter
        return parameter

    def _refresh(self):
        names = [
            p._name  # pylint: disable=protected-access
            for p in six.itervalues(self._parameters)
        ]
        values, invalid_names = self._get_parameters(names, self._with_decryption)
        if invalid_names:
            raise InvalidParameterError(",".join(invalid_names))
        for parameter in six.itervalues(self._parameters):
            parameter._value = values[parameter._name]  # pylint: disable=protected-access

    def __len__(self):
        return len(self._parameters)

class SSMParameter(Refreshable):
    """ Concrete class for an individual SSM Parameter """

    def __init__(self, param_name, max_age=None, with_decryption=True):
        super(SSMParameter, self).__init__(max_age)
        if not param_name:
            raise ValueError("Must specify name")
        self._name = param_name
        self._value = None
        self._with_decryption = with_decryption
        self._group = None

    def _should_refresh(self):
        if self._group:
            return self._group._should_refresh()
        return super(SSMParameter, self)._should_refresh()

    def _refresh(self):
        """ Force refresh of the configured param names """
        if self._group:
            return self._group.refresh()

        values, invalid_parameters = self._get_parameters([self._name], self._with_decryption)
        if invalid_parameters:
            raise InvalidParameterError(self.name)
        self._value = values[self._name]

    @property
    def name(self):
        """ Just an alias """
        return self._name

    @property
    def value(self):
        """ The value of a given param name. """
        if self._value is None or self._should_refresh():
            self.refresh()
        return self._value

def _batch(iterable, num):
    """Turn an iterable into an iterable of batches of size n (or less, for the last one)"""
    length = len(iterable)
    for ndx in range(0, length, num):
        yield iterable[ndx:min(ndx + num, length)]
