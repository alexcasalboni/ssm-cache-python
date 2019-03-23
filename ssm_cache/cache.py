""" Cache module that implements the SSM caching wrapper """
from __future__ import absolute_import, print_function

from datetime import datetime, timedelta
from functools import wraps
import six

from ssm_cache.filters import SSMFilter

class InvalidParameterError(Exception):
    """ Raised when something's wrong with the provided param name """

class InvalidPathError(Exception):
    """ Raised when a given path is not properly structured """

class InvalidVersionError(Exception):
    """ Raised when something's wrong with the provided param version """


class Refreshable(object):
    """ Abstract class for refreshable objects (with max-age) """

    _ssm_client = None

    @classmethod
    def set_ssm_client(cls, client):
        """Override the default boto3 SSM client with your own."""
        required_methods = ('get_parameters', 'get_parameters_by_path')
        for method in required_methods:
            if not hasattr(client, method):
                raise TypeError('client must have a %s method' % method)
        cls._ssm_client = client

    @classmethod
    def _get_ssm_client(cls):
        if cls._ssm_client is None:
            import boto3
            cls._ssm_client = boto3.client('ssm')
        return cls._ssm_client

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

    def _update_refresh_time(self, keep_oldest_value=False):
        """
            Update internal reference with current time.
            Optionally, keep the oldest available reference
            (used by groups with multiple fetch operations at potentially different times)
        """
        now = datetime.utcnow()
        if keep_oldest_value and self._last_refresh_time:
            self._last_refresh_time = min(now, self._last_refresh_time)
        else:
            self._last_refresh_time = now

    def refresh(self):
        """ Updates the value(s) of this refreshable """
        self._refresh()
        # keep track of update date for max_age checks
        self._update_refresh_time()

    @staticmethod
    def _parse_value(param_value, param_type):
        if param_type == 'StringList':
            return param_value.split(',')
        return param_value

    @classmethod
    def _get_parameters(cls, names, with_decryption):
        items = {}
        invalid_names = []
        for name_batch in _batch(names, 10): # can only get 10 parameters at a time
            response = SSMParameter._get_ssm_client().get_parameters(
                Names=list(name_batch),
                WithDecryption=with_decryption,
            )
            invalid_names.extend(response['InvalidParameters'])
            for item in response['Parameters']:
                item['Value'] = cls._parse_value(item['Value'], item['Type'])
                items[item['Name']] = item

        return items, invalid_names

    @classmethod
    def _get_parameters_by_path(cls, with_decryption, path, recursive=True, filters=None):
        """ Return all the parameters under the given path """
        items = {}

        # boto3 paginators doc: http://boto3.readthedocs.io/en/latest/guide/paginators.html
        client = SSMParameter._get_ssm_client()
        has_builtin_paginator = hasattr(client, 'get_paginator')

        def get_pages():
            """ Small utility to implement optional pagination (if native boto3 client) """
            if has_builtin_paginator:
                method = client.get_paginator('get_parameters_by_path').paginate
            else:
                method = client.get_parameters_by_path

            def serialize_filter(filter_obj):
                """ Utility function for serialization """
                if isinstance(filter_obj, SSMFilter):
                    return filter_obj.to_dict()
                return filter_obj

            # result will be a list of pages if built-in pagination
            # otherwise a single "page" is expected
            result = method(
                Path=path,
                Recursive=recursive,
                WithDecryption=with_decryption,
                ParameterFilters=[
                    serialize_filter(filter_obj)
                    for filter_obj in (filters or [])
                ],
            )

            return result if has_builtin_paginator else [result]

        for page in get_pages():
            for item in page['Parameters']:
                item['Value'] = cls._parse_value(item['Value'], item['Type'])
                items[item['Name']] = item

        return items


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
                except error_class:  # pylint: disable=broad-except
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

    def __init__(self, max_age=None, with_decryption=True, base_path=""):
        super(SSMParameterGroup, self).__init__(max_age)

        self._with_decryption = with_decryption
        self._parameters = {}
        self._base_path = base_path or ""
        self._validate_path(base_path)  # may raise

    @staticmethod
    def _validate_path(path):
        if path and not path.startswith("/"):
            raise InvalidPathError("Invalid path: %s (should start with a slash)" % path)

    def parameter(self, path, add_prefix=True):
        """ Create a new SSMParameter by name/path (or retrieve an existing one) """
        if path in self._parameters:
            return self._parameters[path]
        if self._base_path and add_prefix:
            # validate path only if base path is used (otherwise it's just a root name)
            self._validate_path(path)  # may raise
            path = "%s%s" % (self._base_path, path)
        parameter = SSMParameter(path)
        parameter._group = self  # pylint: disable=protected-access
        self._parameters[path] = parameter
        return parameter

    def parameters(self, path, recursive=True, filters=None):
        """ Create new SSMParameter objects by path prefix """
        self._validate_path(path)  # may raise
        if self._base_path:
            path = "%s%s" % (self._base_path, path)
        items = self._get_parameters_by_path(
            with_decryption=self._with_decryption,
            path=path,
            recursive=recursive,
            filters=filters,
        )

        # keep track of update date for max_age checks
        # if a previous call to `parameters` was made, keep that time reference for caching
        self._update_refresh_time(keep_oldest_value=True)

        parameters = []
        # create new parameters and set values
        for name, item in six.iteritems(items):
            parameter = self.parameter(name, add_prefix=False)
            parameter._value = item['Value']  # pylint: disable=protected-access
            parameter._version = item['Version']  # pylint: disable=protected-access
            parameters.append(parameter)
        return parameters

    def secret(self, name):
        """ Create a new SecretsManagerParameter by name (or retrieve an existing one) """
        if name in self._parameters:
            return self._parameters[name]
        parameter = SecretsManagerParameter(name)
        parameter._group = self  # pylint: disable=protected-access
        self._parameters[name] = parameter
        return parameter

    def _refresh(self):
        # pylint: disable=protected-access
        names = [
            param.full_name
            for param in self.get_loaded_parameters()
        ]
        items, invalid_names = self._get_parameters(names, self._with_decryption)
        if invalid_names:
            raise InvalidParameterError(",".join(invalid_names))
        for parameter in self.get_loaded_parameters():
            if parameter.name not in items:
                raise InvalidParameterError(parameter.name)
            parameter._value = items[parameter.name]['Value']
            parameter._version = items[parameter.name]['Version']

    def get_loaded_parameters(self):
        """ Return a list of SSMParameter objects """
        return six.itervalues(self._parameters)

    def __len__(self):
        return len(self._parameters)

class SSMParameter(Refreshable):
    """ Concrete class for an individual SSM Parameter """

    def __init__(self, param_name, max_age=None, with_decryption=True):
        super(SSMParameter, self).__init__(max_age)
        if not param_name:
            raise ValueError("Must specify name")

        self._name, self._version, self._is_pinned_version = self._parse_version(param_name)

        self._value = None
        self._with_decryption = with_decryption
        self._group = None

    @staticmethod
    def _parse_version(param_name):
        """ Extracts version from full name, if provided """

        name, version, is_pinned_version = param_name, None, False

        if ":" in param_name:
            name, version = param_name.split(':')

            if version.isdigit() and int(version) > 0:
                version = int(version)
                is_pinned_version = True
            else:
                raise InvalidVersionError("Invalid version: %s" % version)

        return name, version, is_pinned_version

    def _should_refresh(self):
        if self._group:
            return self._group._should_refresh()  # pylint: disable=protected-access
        return super(SSMParameter, self)._should_refresh()

    def _refresh(self):
        """ Force refresh of the configured param names """
        if self._group:
            self._group.refresh()

        items, invalid_parameters = self._get_parameters([self.full_name], self._with_decryption)
        if invalid_parameters or self._name not in items:
            raise InvalidParameterError("%s is invalid. %s - %s" % (self._name, invalid_parameters, items))
        self._value = items[self._name]['Value']
        self._version = items[self._name]['Version']

    @property
    def name(self):
        """ Just an alias """
        return self._name

    @property
    def full_name(self):
        """ name + version """
        if self._version and self._is_pinned_version:
            return "%s:%s" % (self._name, self._version)
        return self._name

    @property
    def version(self):
        """ Just an alias """
        if self._version is None or self._should_refresh():
            self.refresh()
        return self._version

    @property
    def value(self):
        """ The value of a given param name. """
        if self._value is None or self._should_refresh():
            self.refresh()
        return self._value

class SecretsManagerParameter(SSMParameter):
    """ Concrete class for an individual Secrets Manager parameter """

    PREFIX = "/aws/reference/secretsmanager/"

    def __init__(self, param_name, max_age=None, with_decryption=True):
        param_name = self._add_prefix(param_name)
        super(SecretsManagerParameter, self).__init__(param_name, max_age, with_decryption)

    @classmethod
    def _add_prefix(cls, param_name):
        if not param_name:
            raise ValueError("Secret name can't be empty")
        if not param_name.startswith(cls.PREFIX):
            if param_name.startswith('/'):
                raise InvalidParameterError(param_name)
            param_name = "%s%s" % (cls.PREFIX, param_name)
        return param_name

def _batch(iterable, num):
    """Turn an iterable into an iterable of batches of size n (or less, for the last one)"""
    length = len(iterable)
    for ndx in range(0, length, num):
        yield iterable[ndx:min(ndx + num, length)]
