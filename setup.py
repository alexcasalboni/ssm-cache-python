from setuptools import setup, find_packages

try:
    import pypandoc
    long_description = pypandoc.convert('README.md', 'rst')
except(IOError, ImportError):
    long_description = open('README.md').read()

setup(
    name='ssm-cache',
    version='2.1',
    description='AWS System Manager Parameter Store caching client for Python',
    long_description=long_description,
    keywords = ['aws', 'amazon-web-services', 'aws-lambda', 'aws-ssm', 'parameter-store'],
    license="MIT",
    author='Alex Casalboni',
    author_email='alex@alexcasalboni.com',
    url='https://github.com/alexcasalboni/ssm-cache-python',
    download_url='https://github.com/alexcasalboni/ssm-cache-python/archive/2.1.tar.gz',
    packages=find_packages(),
    install_requires=['boto3==1.5.33', 'future==0.16.0']
)