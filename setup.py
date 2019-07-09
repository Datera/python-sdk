#!/usr/bin/env python

"""
Releasing to PyPI

1. Increment VERSION and VERSION_HISTORY in constants.py

2. Remove the "build" and "dist" folders

3. Run "python setup.py sdist bdist_wheel" to build the wheels

4. Upload to PyPI with "twine upload dist/*"
"""

import io
import os
import re

from setuptools import setup, find_packages

CONSTANTS_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    'src', 'dfs_sdk', 'constants.py')

README_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    'README.md')

VRE = re.compile("""VERSION = ['"](.*)['"]""")


def get_version():
    with io.open(CONSTANTS_FILE) as f:
        return VRE.search(f.read()).group(1)


def get_readme():
    with io.open(README_FILE) as f:
        return f.read()


version = get_version()

setup(
    name='dfs_sdk',
    version=version,
    description='Datera Fabric Python SDK',
    long_description=get_readme(),
    long_description_content_type='text/markdown',
    author='Datera Automation Team',
    author_email='support@datera.io',
    packages=find_packages('src'),
    package_dir={'': 'src'},
    package_data={'dfs_sdk': ['log_cfg/*.json']},
    # include_package_data=True,
    install_requires=[
        "requests",
        "six",
        "urllib3",
    ],
    url='https://github.com/Datera/python-sdk/',
    download_url='https://github.com/Datera/python-sdk/tarball/v{}'.format(
        version),
    classifiers=[
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
    ],
)
