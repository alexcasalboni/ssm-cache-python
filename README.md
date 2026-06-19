AWS System Manager Parameter Store Caching Client for Python
==========================================================

[![CI](https://github.com/alexcasalboni/ssm-cache-python/actions/workflows/ci.yml/badge.svg)](https://github.com/alexcasalboni/ssm-cache-python/actions/workflows/ci.yml)
[![Coverage Status](https://coveralls.io/repos/github/alexcasalboni/ssm-cache-python/badge.svg)](https://coveralls.io/github/alexcasalboni/ssm-cache-python)
[![PyPI version](https://badge.fury.io/py/ssm-cache.svg)](https://badge.fury.io/py/ssm-cache)
[![Python versions](https://img.shields.io/pypi/pyversions/ssm-cache.svg)](https://pypi.org/project/ssm-cache/)
[![GitHub license](https://img.shields.io/github/license/alexcasalboni/ssm-cache-python.svg)](https://github.com/alexcasalboni/ssm-cache-python/blob/master/LICENSE)
[![Maintenance](https://img.shields.io/badge/Maintained%3F-yes-green.svg)](https://GitHub.com/alexcasalboni/ssm-cache-python/graphs/commit-activity)
[![GitHub issues](https://img.shields.io/github/issues/alexcasalboni/ssm-cache-python.svg)](https://github.com/alexcasalboni/ssm-cache-python/issues)
[![GitHub stars](https://img.shields.io/github/stars/alexcasalboni/ssm-cache-python.svg)](https://github.com/alexcasalboni/ssm-cache-python/stargazers)

This module wraps the AWS Parameter Store and adds a caching and grouping layer with max-age invalidation.

You can use this module with AWS Lambda to read and refresh parameters and secrets. Your IAM role will require `ssm:GetParameters` permissions (optionally, also `kms:Decrypt` if you use `SecureString` params).

## Package structure

The library is split into focused modules — import from the top-level `ssm_cache` package for everyday use, or from a specific submodule when you need internals (e.g. for testing or extension).

```
ssm_cache/
├── __init__.py       # public re-exports + __version__
├── exceptions.py     # InvalidParameterError, InvalidPathError, InvalidVersionError
├── filters.py        # SSMFilter, SSMFilterType, SSMFilterKeyId, …
├── groups.py         # SSMParameterGroup
├── parameters.py     # SSMParameter, SecretsManagerParameter
├── refreshable.py    # Refreshable base class (caching, refresh_on_error, set_ssm_client)
└── utils.py          # utcnow(), batch()
```

The version is available at runtime:

```python
import ssm_cache
print(ssm_cache.__version__)  # e.g. "3.0.0"
```

## How to install

```bash
pip install ssm-cache
```

Dev and test dependencies are declared as an optional group in `pyproject.toml` and can be installed with:

```bash
pip install "ssm-cache[dev]"
# or, from a local clone:
pip install -e ".[dev]"
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
param_1 = SSMParameter('param_1', max_age=300)   # 5 min
value_1 = param_1.value

param_2 = SSMParameter('param_2', max_age=3600)  # 1 hour
value_2 = param_2.value
```

### With multiple parameters

You can configure more than one parameter to be fetched, cached, and decrypted as a group.

```python
from ssm_cache import SSMParameterGroup
group = SSMParameterGroup(max_age=300)
param_1 = group.parameter('param_1')
param_2 = group.parameter('param_2')

value_1 = param_1.value
value_2 = param_2.value
```

### With hierarchical parameters

You can fetch and cache a group of parameters under a given prefix. Optionally, the group itself can have its own base path.

```python
from ssm_cache import SSMParameterGroup
group = SSMParameterGroup(base_path="/Foo")
foo_bar = group.parameter('/Bar')      # fetches /Foo/Bar
baz_params = group.parameters('/Baz') # fetches /Foo/Baz/1, /Foo/Baz/2, …

assert len(group) == 3
```

`group.parameters(...)` can be called multiple times. When caching is enabled, the group's expiry is anchored to the earliest `parameters()` call, so all prefixes age out together.

#### Hierarchical parameters and filters

Filter by parameter `Type` or KMS `KeyId`, either with a raw dict or a typed class (which validates values before the API call).

```python
from ssm_cache import SSMParameterGroup
from ssm_cache.filters import SSMFilterType, SSMFilterKeyId

group = SSMParameterGroup()

# raw dict
params = group.parameters(
    path="/Foo/Bar",
    filters=[{'Key': 'Type', 'Option': 'Equals', 'Values': ['StringList']}],
)

# typed class — validates allowed values before calling the API
params = group.parameters(
    path="/Foo/Bar",
    filters=[SSMFilterType().value('StringList')],
)

# KeyId filter, begins-with
params = group.parameters(
    path="/Foo/Bar",
    filters=[SSMFilterKeyId('BeginsWith').value('alias/')],
)
```

#### Non-recursive fetch

```python
from ssm_cache import SSMParameterGroup
group = SSMParameterGroup()

# fetches /Foo/1, /Foo/2 but NOT /Foo/Bar/1
params = group.parameters(path="/Foo", recursive=False)
```

### With StringList parameters

`StringList` parameters are automatically split on commas and returned as Python lists.

```python
from ssm_cache import SSMParameter
# "my_twitter_api_keys" is a StringList (four comma-separated values)
twitter_params = SSMParameter('my_twitter_api_keys')
key, secret, access_token, access_token_secret = twitter_params.value
```

### Explicit refresh

Force a refresh on a parameter or group at any time. When a parameter belongs to a group, refreshing it refreshes the whole group.

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

group.refresh()           # refreshes all params in the group
param_1.refresh()         # also refreshes the whole group
```

### Without decryption

Decryption is enabled by default. Disable it explicitly for `SSMParameter` or `SSMParameterGroup`.

```python
from ssm_cache import SSMParameter
param = SSMParameter('my_param_name', with_decryption=False)
value = param.value
```

### AWS Secrets Manager integration

`SecretsManagerParameter` provides the same interface as `SSMParameter` and transparently accesses Secrets Manager values via the SSM parameter path `/aws/reference/secretsmanager/<name>`.

```python
from ssm_cache import SecretsManagerParameter
secret = SecretsManagerParameter('my_secret_name')
value = secret.value
```

Secrets can be mixed with regular parameters inside a `SSMParameterGroup`. No group base path is applied to secrets.

```python
from ssm_cache import SSMParameterGroup
group = SSMParameterGroup()
param  = group.parameter('my_param')
secret = group.secret('my_secret')

param_value  = param.value
secret_value = secret.value
```

Passing a name that starts with `/` raises `InvalidParameterError` immediately, since that would be ambiguous with a raw SSM path.

### Versioning support

SSM Parameter Store supports [version selectors](https://docs.aws.amazon.com/systems-manager/latest/userguide/sysman-paramstore-versions.html). Omitting the version always fetches the latest.

```python
from ssm_cache import SSMParameter

# always fetches the latest version
param = SSMParameter('my_param_name')
print(param.version)  # int

# pinned to version 2 — refresh() will NOT advance to a newer version
param_v2 = SSMParameter('my_param_name:2')
value = param_v2.value
```

## Usage with AWS Lambda

Parameters and secrets are initialised once outside the handler, so the cache persists across warm invocations.

```python
from ssm_cache import SSMParameter, SecretsManagerParameter

param  = SSMParameter('my_param_name', max_age=300)
secret = SecretsManagerParameter('my_secret_name', max_age=300)

def lambda_handler(event, context):
    dbname   = param.value
    password = secret.value
    return f'Hello from Lambda with dbname {dbname}'
```

## Complex invalidation based on signals

Explicitly call `refresh()` when an application-level error signals that a cached value is stale.

```python
from ssm_cache import SSMParameter
from my_db_lib import Client, InvalidCredentials  # pseudo-code

param = SSMParameter('my_db_password')
my_db_client = Client(password=param.value)

def read_record(is_retry=False):
    try:
        return my_db_client.read_record()
    except InvalidCredentials:
        if not is_retry:
            param.refresh()
            my_db_client = Client(password=param.value)
            return read_record(is_retry=True)

def lambda_handler(event, context):
    return {'record': read_record()}
```

## Decorator utility

`refresh_on_error` codifies the retry pattern above as a decorator on any `SSMParameter` or `SSMParameterGroup` instance.

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
    return {'record': read_record()}
```

`refresh_on_error` accepts:

| Argument | Default | Description |
|---|---|---|
| `error_class` | `Exception` | Exception type to intercept |
| `error_callback` | `None` | Called after refresh, before retry |
| `retry_argument` | `"is_retry"` | Kwarg name injected on retry |

## Replacing the SSM client

`set_ssm_client` lives on `Refreshable`, the base class shared by `SSMParameter` and `SSMParameterGroup`. Call it on whichever class you want to override, or on `Refreshable` directly to affect all subclasses at once.

```python
from ssm_cache.refreshable import Refreshable

# affects SSMParameter, SSMParameterGroup, and any subclass
Refreshable.set_ssm_client(my_custom_client)
```

The replacement object must implement two methods: `get_parameters` and `get_parameters_by_path`.

A common use case is injecting a [Placebo](https://github.com/garnaat/placebo) client for offline or unit testing:

```python
import boto3, placebo
from ssm_cache.refreshable import Refreshable

session = boto3.Session()
pill = placebo.attach(session, data_path='/path/to/responses')
pill.playback()

Refreshable.set_ssm_client(session.client('ssm'))
```

## How to contribute

Clone the repo and install all dev dependencies in one step:

```bash
git clone https://github.com/alexcasalboni/ssm-cache-python.git
cd ssm-cache-python
python -m venv env
source env/bin/activate
pip install -e ".[dev]"
```

### Running the tests

```bash
pytest
```

With coverage:

```bash
pytest --cov=ssm_cache --cov-report=term-missing
```

HTML coverage report:

```bash
pytest --cov=ssm_cache --cov-report=html
open htmlcov/index.html
```

### Linting and formatting

The project uses [ruff](https://docs.astral.sh/ruff/) for both linting and formatting.

Check for lint violations:

```bash
ruff check .
```

Auto-fix all fixable violations:

```bash
ruff check --fix .
```

Check formatting:

```bash
ruff format --check .
```

Apply formatting:

```bash
ruff format .
```

The CI `lint` job runs both `ruff format --check` and `ruff check` on every push and pull request before the test matrix starts. A failing lint check blocks the test run.

Opening a PR triggers the GitHub Actions CI matrix across Python 3.10–3.14 and uploads coverage to Coveralls automatically.

### Test layout

Test files mirror the package modules:

| Test file | Covers |
|---|---|
| `tests/test_utils.py` | `ssm_cache.utils` — `utcnow`, `batch` |
| `tests/test_refreshable.py` | `ssm_cache.refreshable` — `Refreshable`, `refresh_on_error`, `set_ssm_client` |
| `tests/test_parameters.py` | `ssm_cache.parameters` — `SSMParameter` |
| `tests/test_groups.py` | `ssm_cache.groups` — `SSMParameterGroup`, hierarchy |
| `tests/test_filters.py` | `ssm_cache.filters` — `SSMFilter` and subclasses |
| `tests/test_secrets.py` | `SecretsManagerParameter` |
| `tests/test_versioning.py` | Versioning and version pinning (placebo-backed) |

## What's new?

* **version 3.0.0**: 
  * dropped support for Python <3.10 (3.8 and 3.9 are end-of-life)
  * Python 3.10–3.14 supported and tested
  * fully type-annotated; ships a `py.typed` marker (PEP 561) and is type-checked with mypy
  * split monolithic `cache.py` into logically grouped modules (`exceptions`, `filters`, `groups`, `parameters`, `refreshable`, `utils`)
  * `__version__` added to package
  * `pyproject.toml` replaces `setup.py` and `requirements*.txt`
  * `set_ssm_client` promoted to `Refreshable` base class
  * `ParameterNotFound` ClientError now normalised to `InvalidParameterError`
  * test suite restructured to mirror package layout
  * ruff replaces pylint for linting and formatting
  * migrated from Travis to GitHub Actions
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
