AWS System Manager Parameter Store Caching Client for Python ([![Python 2.7](https://img.shields.io/badge/python-2.7-green.svg)](https://www.python.org/downloads/release/python-270/) [![Python 3.6](https://img.shields.io/badge/python-3.6-green.svg)](https://www.python.org/downloads/release/python-360/) [![Python 3.7](https://img.shields.io/badge/python-3.7-green.svg)](https://www.python.org/downloads/release/python-370/))
==========================================================

[![Build Status](https://travis-ci.org/alexcasalboni/ssm-cache-python.svg?branch=master)](https://travis-ci.org/alexcasalboni/ssm-cache-python)
[![Coverage Status](https://coveralls.io/repos/github/alexcasalboni/ssm-cache-python/badge.svg)](https://coveralls.io/github/alexcasalboni/ssm-cache-python)
[![PyPI version](https://badge.fury.io/py/ssm-cache.svg)](https://badge.fury.io/py/ssm-cache)
[![GitHub license](https://img.shields.io/github/license/alexcasalboni/ssm-cache-python.svg)](https://github.com/alexcasalboni/ssm-cache-python/blob/master/LICENSE)
[![Maintenance](https://img.shields.io/badge/Maintained%3F-yes-green.svg)](https://GitHub.com/alexcasalboni/ssm-cache-python/graphs/commit-activity)
[![GitHub issues](https://img.shields.io/github/issues/alexcasalboni/ssm-cache-python.svg)](https://github.com/alexcasalboni/ssm-cache-python/issues)
[![Open Source Love svg2](https://badges.frapsoft.com/os/v2/open-source.svg?v=103)](https://github.com/ellerbrock/open-source-badges/)
[![GitHub stars](https://img.shields.io/github/stars/alexcasalboni/ssm-cache-python.svg)](https://github.com/alexcasalboni/ssm-cache-python/stargazers)





This module wraps the AWS Parameter Store and adds a caching and grouping layer with max-age invalidation.

You can use this module with AWS Lambda to read and refresh parameters and secrets. Your IAM role will require `ssm:GetParameters` permissions (optionally, also `kms:Decrypt` if you use `SecureString` params).

## How to install

Install the module with `pip`:

```bash
pip install ssm-cache
```

## How to use it

### Simplest use case

A single parameter, configured by name.

```python
from ssm_cache import SSMParameter
param = SSMParameter('my_param_name')
value = param.value
```

### With cache invalidation

You can configure the `max_age` in seconds, after which the values will be automatically refreshed.

```python
from ssm_cache import SSMParameter
param_1 = SSMParameter('param_1', max_age=300)  # 5 min
value_1 = param.value

param_2 = SSMParameter('param_2', max_age=3600)  # 1 hour
value_2 = param_2.value
```
### With multiple parameters

You can configure more than one parameter to be fetched/cached/decrypted as a group.

```python
from ssm_cache import SSMParameterGroup
group = SSMParameterGroup(max_age=300)
param_1 = group.parameter('param_1')
param_2 = group.parameter('param_2')

value_1 = param_1.value
value_2 = param_2.value
```

### With hierarchical parameters

You can fetch/cache a group of parameters under a given prefix. Optionally, the group itself could have its own base path.

```python
from ssm_cache import SSMParameterGroup
group = SSMParameterGroup(base_path="/Foo")
foo_bar = group.parameter('/Bar')  # will fetch /Foo/Bar
baz_params = group.parameters('/Baz')  # will fetch /Foo/Baz/1 and /Foo/Baz/2

assert len(group) == 3
```

Note: you can call `group.parameters(...)` multiple times. If caching is enabled, the group's cache will expire when the firstly fetched parameters expire.

#### Hierarchical parameters and filters

You can filter by parameter `Type` and KMS `KeyId`, either building the filter object manually or using a class-based approach (which provides some additional checks before invoking the API).

```python
from ssm_cache import SSMParameterGroup
from ssm_cache.filters import SSMFilterType

group = SSMParameterGroup()

# manual filter definition
params = group.parameters(
    path="/Foo/Bar",
    filters=[{
        'Key': 'Type',
        'Option': 'Equals',
        'Values': ['StringList']
    }],
)

# class-based filter
params = group.parameters(
    path="/Foo/Bar",
    filters=[SSMFilterType().value('StringList')],  # will validate allowed value(s)
)
```

#### Hierarchical parameters and non-recursiveness

You can disable recursion when fetching parameters via prefix.

```python
from ssm_cache import SSMParameterGroup
group = SSMParameterGroup()

# will fetch /Foo/1, but not /Foo/Bar/1
params = group.parameters(
    path="/Foo",
    recursive=False,
)
```

### With StringList parameters

`StringList` parameters ([documentation here](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/aws-resource-ssm-parameter.html#cfn-ssm-parameter-type)) are automatically converted to Python lists with no additional configuration.

```python
from ssm_cache import SSMParameter
# "my_twitter_api_keys" is a StringList parameter (four comma-separated values)
twitter_params = SSMParameter('my_twitter_api_keys')
key, secret, access_token, access_token_secret = twitter_params.value
```
### Explicit refresh

You can manually force a refresh on a parameter or parameter group.
Note that if a parameter is part of a group, the refresh operation will involve the entire group.

```python
from ssm_cache import SSMParameter
param = SSMParameter('my_param_name')
value = param.value
param.refresh()
new_value = param.value
```

```python
from ssm_cache import SSMParameterGroup
group = SSMParameterGroup()
param_1 = group.parameter('param_1')
param_2 = group.parameter('param_2')

value_1 = param_1.value
value_2 = param_2.value

group.refresh()
new_value_1 = param_1.value
new_value_2 = param_2.value

param_1.refresh()
new_new_value_1 = param_1.value
new_new_value_2 = param_2.value # one parameter refreshes the whole group
```

### Without decryption

Decryption is enabled by default, but you can explicitly disable it (works for `SSMParameter` and `SSMGroup`).

```python
from ssm_cache import SSMParameter
param = SSMParameter('my_param_name', with_decryption=False)
value = param.value
```

### AWS Secrets Manager Integration

You can read [AWS Secrets Manager](https://aws.amazon.com/secrets-manager/) secrets transparently by using the `SecretsManagerParameter` class, which comes with the same interface of `SSMParameter` and performs some additional prefixing and validation.

```python
from ssm_cache import SecretsManagerParameter
secret = SecretsManagerParameter('my_secret_name')
value = secret.value
```

Secrets can be added to a `SSMParameterGroup` as well, although no group prefix will be applied.


```python
from ssm_cache import SSMParameterGroup
group = SSMParameterGroup()
param = group.parameter('my_param')
secret = group.secret('my_secret')

param_value = param.value
secret_value = secret.value
```

### Versioning support

SSM Parameter Store supports version selectors ([documentation here](https://docs.aws.amazon.com/systems-manager/latest/userguide/sysman-paramstore-versions.html)).

By default, the latest version is fetched if you don't specify it.

Here is how you can retrieve a specific parameter version:

```python
from ssm_cache import SSMParameter
param = SSMParameter('my_param_name:2')
value = param.value
```

Please note that invoking `param.refresh()` will not fetch newer versions. This is the intended behavior, as version selection should be used only when you need a specific parameter version.

If you don't specify any version, you can always read the current version of a parameter. In this case, invoking `param.refresh()` will invoke the new version.


```python
from ssm_cache import SSMParameter
param = SSMParameter('my_param_name')
print(param.version)  # will print an int
```



## Usage with AWS Lambda

Your [AWS Lambda](https://aws.amazon.com/lambda/) code will look similar to the following snippet.

```python
from ssm_cache import SSMParameter, SecretsManagerParameter
param = SSMParameter('my_param_name')
secret = SecretsManagerParameter('my_secret_name')

def lambda_handler(event, context):
    dbname = param.value
    password = secret.value
    return 'Hello from Lambda with dbname %s and password %s' % (dbname, password)

```

## Complex invalidation based on "signals"

You may want to explicitly refresh the parameter cache when you believe the cached value expired.

In the example below, we refresh the parameter value when an `InvalidCredentials` exception is detected (see the [decorator utility](#decorator-utility) for a simpler version!).

```python
from ssm_cache import SSMParameter
from my_db_lib import Client, InvalidCredentials  # pseudo-code

param = SSMParameter('my_db_password')
my_db_client = Client(password=param.value)

def read_record(is_retry=False):
    try:
        return my_db_client.read_record()
    except InvalidCredentials:
        if not is_retry:  # avoid infinite recursion
            param.refresh()  # force parameter refresh
            my_db_client = Client(password=param.value)  # re-configure db client
            return read_record(is_retry=True)  # let's try again :)

def lambda_handler(event, context):
    return {
        'record': read_record(),
    }
```

## Decorator utility

The retry logic shown above can be simplified with the decorator method provided by each `SSMParameter` and `SSMParameterGroup` object.

The `@refresh_on_error` decorator will intercept errors (or a specific `error_class`, if given), refresh the parameters values, and attempt to re-call the decorated function. Optionally, you can provide a `callback` argument to implement your own logic (in the example below, to create a new db client with the new password).

```python
from ssm_cache import SSMParameter
from my_db_lib import Client, InvalidCredentials  # pseudo-code

param = SSMParameter('my_db_password')
my_db_client = Client(password=param.value)

def on_error_callback():
    my_db_client = Client(password=param.value)

@param.refresh_on_error(InvalidCredentials, on_error_callback)
def read_record(is_retry=False):
    return my_db_client.read_record()

def lambda_handler(event, context):
    return {
        'record': read_record(),
    }
```


The `refresh_on_error` decorator supports the following arguments:

* **error_class** (default: `Exception`)
* **error_callback** (default: `None`)
* **retry_argument** (default: `"is_retry"`)

## Replacing the SSM client

If you want to replace the default `boto3` SSM client, `SSMParameter` allows you to call `set_ssm_client` and provide your own `boto3` client or even a custom object. Note that such custom object will need to implement two methods: `get_parameters` and `get_parameters_by_path`.

For example, here's how you could inject a Placebo client for local tests:

```python
import placebo, boto3
from ssm_cache import SSMParameter

# create regular boto3 session
session = boto3.Session()
# attach placebo to the session
pill = placebo.attach(session, data_path=PLACEBO_PATH)
pill.playback()
# create special boto3 client
client = session.client('ssm')
# inject special client into SSMParameter or SSMParameterGroup
SSMParameter.set_ssm_client(client)
```

## How to contribute

Clone this repository, create a virtualenv and install all the dev dependencies:

```bash
git clone https://github.com/alexcasalboni/ssm-cache-python.git
cd ssm-cache-python
virtualenv env
source env/bin/activate
pip install -r requirements-dev.txt
```

You can run tests with `nose`:

```bash
nosetests
```

Generate a coverage report:

```bash
nosetests --with-coverage --cover-erase --cover-html --cover-package=ssm_cache
open cover/index.html
```

Run pylint:

```bash
pylint ssm_cache
```

Note: when you open a new PR, GitHub will run tests on multiple Python environments and verify the new coverage for you, but we highly recommend you run these tasks locally as well before submitting new code.

## What's new?

* **version 2.10**: exclude tests folder from site-packages
* **version 2.9**: bugfix, versioning support, tests with Python 3.7
* **version 2.8**: bugfix, new tests, fixed Travis build config
* **version 2.7**: support for AWS Secrets Manager integration
* **version 2.5**: hierarchical parameters, filters, and non-recursiveness support
* **version 2.3**: StringList parameters support (auto-conversion)
* **version 2.2**: client replacement and boto3/botocore minimum requirements
* **version 2.1**: group refresh bugfix
* **version 2.0**: new interface, `SSMParameterGroup` support
* **version 1.3**: Python3 support
* **version 1.0**: initial release

## References and articles

* [You should use SSM Parameter Store over Lambda env variables](https://hackernoon.com/you-should-use-ssm-parameter-store-over-lambda-env-variables-5197fc6ea45b) by Yan Cui (similar Node.js implementation)
* [AWS System Manager Parameter Store doc](https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-paramstore.html)
