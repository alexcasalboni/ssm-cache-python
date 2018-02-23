"""Parameter store that reads from AWS Systems Manager Parameter Store"""
from __future__ import absolute_import, print_function

from .store import ParameterStore

class SSMParameterStore(ParameterStore): # pylint: disable=too-few-public-methods
    """Concrete ParameterStore that reads from AWS Systems Manager Parameter Store

    The class provides an _ssm_client() method that caches the client in the class,
    reducing overhead in the Lambda invocations. These relies on the _session() method,
    which in turn uses SESSION_FACTORY if it is set, allowing overriding with mock sessions
    for testing. Similarly, CLIENT_FACTORY can be set to a callable that take a session and a name
    to override client creation.

    Some hooks are provided to override behavior. These are class fields, since they are called
    by a class method.
    * SESSION_FACTORY takes no input and returns an object that acts like a boto3 session.
        If this class field is not None, it is used by _session() instead of creating
        a regular boto3 session. This could be made to use placebo for testing
        https://github.com/garnaat/placebo
    * BOTO3_CLIENT_FACTORY takes the AWS service name (as defined in boto3) as input and returns
    * CLIENT_FACTORY takes the AWS service name (as defined in boto3) as input and returns
        an object that acts like a boto3 client. If this class field is not None, it is used by
        get_boto3_client() instead of creating a regular boto3 client.
    """

    @classmethod
    def _default_session_factory(cls):
        """Default session factory that creates a boto3 session."""
        import boto3
        return boto3.session.Session()

    @classmethod
    def _default_client_factory(cls, session, name):
        """Default client factory that creates a client from the provided session."""
        return session.client(name)

    SESSION_FACTORY = _default_session_factory
    CLIENT_FACTORY = _default_client_factory

    _SESSION = None
    _CLIENT = None

    @classmethod
    def _session(cls):
        """Use the defined session factory to create an object that acts like a boto3 session.
        Defaults to boto3.session.Session(); set SESSION_FACTORY to inject a different session
        factory."""
        if cls._SESSION is None:
            if cls.SESSION_FACTORY:
                cls._SESSION = cls.SESSION_FACTORY()
            else:
                cls._SESSION = cls._default_session_factory()
        return cls._SESSION

    @classmethod
    def _client(cls):
        """Use the defined client factory to create an object that acts like a boto3 client.
        Defaults to _session().client("ssm"); set CLIENT_FACTORY to inject a different client
        factory."""
        if cls._CLIENT is None:
            if cls.CLIENT_FACTORY:
                client = cls.CLIENT_FACTORY(cls._session(), "ssm")
            else:
                client = cls._default_client_factory(cls._session(), "ssm")
            cls._CLIENT = client
        return cls._CLIENT

    @classmethod
    def _batch(cls, iterable, num):
        """Turn an iterable into an iterable of batches of size n (or less, for the last one)"""
        length = len(iterable)
        for ndx in range(0, length, num):
            yield iterable[ndx:min(ndx + num, length)]

    def parameters(self, names, with_decryption):
        """Retrieve the named parameters from the AWS Systems Manager Parameter Store."""
        values = {}
        invalid_names = []
        for name_batch in self._batch(names, 10): # can only get 10 parameters at a time
            response = self._client().get_parameters(
                Names=list(name_batch),
                WithDecryption=with_decryption,
            )
            invalid_names.extend(response['InvalidParameters'])
            for item in response['Parameters']:
                values[item['Name']] = item['Value']

        return values, invalid_names
