""" Cache module that implements the SSM caching wrapper """
from datetime import datetime, timedelta
import boto3


class InvalidParam(Exception):
    """ Raised when something's wrong with the provided param name """

class SSMParameter(object):
    """ The class wraps an SSM Parameter and adds optional caching """

    ssm_client = boto3.client('ssm')

    def __init__(self, param_names=None, max_age=None, with_decryption=True):
        if isinstance(param_names, basestring):
            param_names = [param_names]
        if not param_names:
            raise ValueError("At least one parameter should be configured")
        self._names = param_names
        self._values = {}
        self._with_decryption = with_decryption
        self._last_refresh_time = None
        self._max_age = max_age
        self._max_age_delta = timedelta(seconds=max_age or 0)

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
        """ Force refresh of the configured param names """
        response = self.ssm_client.get_parameters(
            Names=self._names,
            WithDecryption=self._with_decryption,
        )
        # create a dict of name:value for each param
        self._values = {
            param['Name']: param['Value']
            for param in response['Parameters']
        }
        # keep track of update date for max_age checks
        self._last_refresh_time = datetime.utcnow()

    def value(self, name=None):
        """
            Retrieve the value of a given param name.
            If only one name is configured, the name can be omitted.
        """
        # transform single string into list (syntactic sugar)
        if name is None:
            # name is required, unless only one parameter is configured
            if len(self._names) == 1:
                name = self._names[0]
            else:
                raise TypeError("Parameter name is required (None was given)")
        if name not in self._names:
            raise InvalidParam("Parameter %s is not configured" % name)
        if name not in self._values or self._should_refresh():
            self.refresh()
        try:
            return self._values[name]
        except KeyError:
            raise InvalidParam("Param '%s' does not exist" % name)

    def values(self, names=None):
        """
            Retrieve a list of values.
            If no name is provided, all values are returned.
        """
        if not names:
            names = self._names
        return [self.value(name) for name in names]

