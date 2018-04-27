""" Setup command """
from setuptools import setup, find_packages

try:
    import pypandoc
    LONG_DESCRIPTION = pypandoc.convert('README.md', 'rst')
except(IOError, ImportError):
    LONG_DESCRIPTION = open('README.md').read()

setup(
    name='ssm-cache',
    version='2.5',
    description='AWS System Manager Parameter Store caching client for Python',
    long_description=LONG_DESCRIPTION,
    keywords=['aws', 'amazon-web-services', 'aws-lambda', 'aws-ssm', 'parameter-store'],
    license="MIT",
    author='Alex Casalboni',
    author_email='alex@alexcasalboni.com',
    url='https://github.com/alexcasalboni/ssm-cache-python',
    download_url='https://github.com/alexcasalboni/ssm-cache-python/archive/2.5.tar.gz',
    packages=find_packages(),
    install_requires=['boto3', 'future'],
)
