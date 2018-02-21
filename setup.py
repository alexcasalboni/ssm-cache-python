from setuptools import setup, find_packages

with open("README", 'r') as f:
    long_description = f.read()

setup(
    name='ssm_cache',
    version='0.1',
    description='AWS System Manager Parameter Store caching client for Python',
    long_description=long_description,
    license="MIT",
    author='Alex Casalboni',
    author_email='alex@alexcasalboni.com',
    url='https://github.com/alexcasalboni/ssm-cache-python',
    packages=find_packages(),
    install_requires=['awscli==1.14.43']
)