#!/usr/bin/env

from setuptools import setup

setup(
    name='dfs_sdk',
    version='1.1.0',
    description='Datera Fabric Python SDK',
    long_description='Install Instructions: sudo python setup.py install',
    author='Datera Automation Team',
    author_email='support@datera.io',
    packages=['dfs_sdk'],
    package_dir={'': 'src'},
    package_data={'dfs_sdk': ['logging.json']},
    include_package_data=True,
    install_requires=[],
    scripts=['utils/dhutil'],
    url='https://github.com/Datera/python-sdk/',
    download_url='https://github.com/Datera/python-sdk/tarball/v1.1.0'
)
