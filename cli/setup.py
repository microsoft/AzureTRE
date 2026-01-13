#!/usr/bin/env python

from setuptools import find_packages
from setuptools import setup

PROJECT = 'azure-tre-cli'
VERSION = '0.2.7'

try:
    long_description = open('README.md', 'rt').read()
except IOError:
    long_description = ''

setup(
    name=PROJECT,
    version=VERSION,

    description='Experimental TRE CLI for AzureTRE',
    long_description=long_description,

    author='Stuart Leeks',
    author_email='stuartle@microsoft.com',

    # url='',
    # download_url='',

    classifiers=[
        'Development Status :: 3 - Alpha',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3 :: Only',
        'Intended Audience :: Developers',
        'Environment :: Console',
    ],

    platforms=['Any'],

    scripts=[],

    provides=[],
    install_requires=[
        "click==8.1.3",
        "httpx==0.28.1",
        "msal==1.31.1",
        "jmespath==1.0.1",
        "tabulate==0.9.0",
        "pygments==2.19.2",
        "PyJWT==2.10.1",
        "azure-cli-core==2.68.0",
        "azure-identity==1.25.1",
        "aiohttp==3.13.3"
    ],

    namespace_packages=[],
    packages=find_packages(),
    include_package_data=True,

    entry_points={
        'console_scripts': [
            'tre = tre.main:cli'
        ],
    },

    zip_safe=False,
)
