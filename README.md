AWS System Manager Parameter Store Caching Client (Python)
==========================================================


This module wraps the AWS Parameter Store and adds a caching layer with max-age invalidation.

You can use this module with AWS Lambda to read and refresh sensitive parameters. Your IAM role will require `ssm:GetParameters` permissions (optionally, also `kms:Decrypt` if you use `SecureString` params).

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
value = param.value()
```

### With cache invalidation

You can configure the `max_age` in seconds, after which the values will be automatically refreshed.

```python
from ssm_cache import SSMParameter
param = SSMParameter('my_param_name', max_age=300)  # 5 min
value = param.value()
```

### With multiple parameters

You can configure more than one parameter to be fetched/cached together.

```python
from ssm_cache import SSMParameter
params = SSMParameter(['param_1', 'param_2'])
value_1, value_2 = params.values()
# or individually
value_1 = params.value('param_1')
```

### Explicit refresh

You can manually force a refresh for all the configured parameters.

```python
from ssm_cache import SSMParameter
param = SSMParameter('my_param_name')
value = param.value()
param.refresh()
new_value = param.value()
```

### Multiple cache behaviors

If you need different cache behaviour for each parameter, you can simply create more than one `SSMParameter` object.

```python
from ssm_cache import SSMParameter
param_1 = SSMParameter('param_1', max_age=300)  # 5 min
param_2 = SSMParameter('param_2', max_age=3600)  # 1 hour
value_1 = param_1.value()
value_2 = param_2.value()
```

### Without decryption

Decryption is enabled by default, but you can explicitly disable it.

```python
from ssm_cache import SSMParameter
param = SSMParameter('my_param_name', with_decryption=False)
value = param.value()
```

## Usage with AWS Lambda

Your AWS Lambda code will look similar to the following snippet.

```python
from ssm_cache import SSMParameter
param = SSMParameter('my_param_name')

def lambda_handler(event, context):
    secret_value = param.value()
    return 'Hello from Lambda with secret %s' % secret_value

```

## Complex invalidation based on "signals"

You may want to explicitly refresh the parameter cache when you believe the cached value expired.

In the example below, we refresh the parameter value when an `InvalidCredentials` exception is detected (see the [decorator utility](#decorator-utility) for a simpler version!).

```python
from ssm_cache import SSMParameter
from my_db_lib import Client, InvalidCredentials  # pseudo-code

param = SSMParameter('my_db_password')
my_db_client = Client(password=param.value())

def read_record(is_retry=False):
    try:
        return my_db_client.read_record()
    except InvalidCredentials:
        if not is_retry:  # avoid infinite recursion
            param.refresh()  # force parameter refresh
            my_db_client = Client(password=param.value())  # re-configure db client
            return read_record(is_retry=True)  # let's try again :)

def lambda_handler(event, context):
    return {
        'record': read_record(),
    }
```

## Decorator utility

The retry logic shown above can be simplified with the decorator method provided by each `SSMParameter` object.

The `@param.refresh_on_error` decorator will intercept errors (or a specific `error_class`, if given), refresh the parameters values, and attempt to re-call the decorated function. Optionally, you can provide a `callback` argument to implement your own logic (in the example below, to create a new db client with the new password).

```python
from ssm_cache import SSMParameter
from my_db_lib import Client, InvalidCredentials  # pseudo-code

param = SSMParameter('my_db_password')
my_db_client = Client(password=param.value())

def on_error_callback():
    my_db_client = Client(password=param.value())

@param.refresh_on_error(InvalidCredentials, on_error_callback)
def read_record(is_retry=False):
    return my_db_client.read_record()

def lambda_handler(event, context):
    return {
        'record': read_record(),
    }
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

## References and articles

* [You should use SSM Parameter Store over Lambda env variables](https://hackernoon.com/you-should-use-ssm-parameter-store-over-lambda-env-variables-5197fc6ea45b) by Yan Cui (similar Node.js implementation)
* [AWS System Manager Parameter Store doc](https://docs.aws.amazon.com/systems-manager/latest/userguide/systems-manager-paramstore.html)