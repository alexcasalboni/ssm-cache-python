from setuptools import setup, find_packages

setup(
    name='ssm-cache',
    version='1.0',
    description='AWS System Manager Parameter Store caching client for Python',
    author='Alex Casalboni',
    author_email='alex@alexcasalboni.com',
    url='https://github.com/alexcasalboni/ssm-cache-python',
    packages=find_packages(),
    install_requires=['awscli==1.14.43']
)