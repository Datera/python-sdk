# Datera Python SDK


## Introduction

This is Python SDK version 0.1 for the **Datera** Fabric Services API.
Download and use of this package implicitly accepts the terms in COPYING

Users of this package are assumed to have familiarity with the **Datera** API.
Details around the API itself are not necessarily covered through this SDK.


## Installation

To install:
```bash
    apt-get install python-virtualenv (or yum install python-virtualenv for CentOS)
    virtualenv sdk
    source sdk/bin/activate
    git clone https://github.com/Datera/python-sdk.git
    cd python-sdk
    pip install -r requirements.txt
    python setup.py install
```

## Universal Datera Config

The Universal Datera Config (UDC) is a config that can be specified in a
number of ways:

* JSON file with any of the following names:
    [.datera-config, datera-config, .datera-config.json, dateraconfig.json]
* The JSON file has the following configuration:
```json
     {"mgmt_ip": "1.1.1.1",
      "username": "admin",
      "password": "password",
      "tenant": "/root",
      "api_version": "2.2"'
      "ldap": ""}
```
* The file can be in any of the following places.  This is also the lookup
  order for config files:
    current directory --> home directory --> home/config directory --> /etc/datera
* If no datera config file is found and a cinder.conf file is present, the
  config parser will try and pull connection credentials from the
  cinder.conf
* Tenant and API version and LDAP are always optional, but it's generally
  suggested to include them in your UDC file for easy reference.
* Instead of a JSON file, environment variables can be used.
    - `DAT_MGMT`
    - `DAT_USER`
    - `DAT_PASS`
    - `DAT_TENANT`
    - `DAT_API`
    - `DAT_LDAP`
* Most tools built to use the Universal Datera Config will also allow
  for providing/overriding any of the config values via command line flags.
    - --hostname
    - --username
    - --password
    - --tenant
    - --api-version
    - --ldap

## Developing with Universal Datera Config

To use UDC in a new python tool is very simple just add the following to
your python script:

```python
from dfs_sdk import scaffold

parser = scaffold.get_argparser()
parser.add_argument('my-new-arg')
args = parser.parse_args()
```

If you want to use subparsers, or customize the help outptu of your parser
then use the following

```python
import argparse
from dfs_sdk import scaffold

top_parser = scaffold.get_argparser(add_help=False)
new_parser = argparse.ArgumentParser(parents=[top_parser])
new_parser.add_argument('my-new-arg')
args = new_parser.parse_args()
```

Inside a script the config can be recieved by calling
```python
from dfs_sdk import scaffold

scaffold.get_argparser()
config = scaffold.get_config()
```
NOTE: You MUST call ``scaffold.get_argparser()`` before calling
``scaffold.get_config()``.  This may change in the future

## Logging

To set custom logging.json file
```bash
    export DSDK_LOG_CFG=your/log/location.json
```
Or the value can be set to a debug, info or error
```bash
    export DSDK_LOG_CFG=info
```

To set logging to stdout.  The value can be any logging level supported by
the python logging module (eg: debug, info, etc)
```bash
    export DSDK_LOG_STDOUT=debug
```

The debug logs generated by the python-sdk are quite large, and are on a
rotating file handler (provided that a custom logging.json file is not provided)

## Managed Objects

Datera provides an application-driven storage management model, whose goal is to closely align storage
with a corresponding application's requirements.

The main storage objects are defined and differentiated as follows:

### Application Instance (AppInstance)
    -    Corresponds to an application, service, etc.
    -    Contains Zero or more Storage Instances

### Storage Instance
    -    Corresponds to one set of storage requirements for a given AppInstance
    -    ACL Policies, including IQN Initiators
    -    Target IQN
    -    Contains Zero or more Volumes

### Volumes
    -    Corresponds to a single allocated storage object
    -    Size (default unit is GB)
    -    Replication Factor
    -    Performance Policies (QoS for Bandwidth and IOPS)
    -    Protection Policies (Snapshot scheduling)

Another way of viewing the managed object hierarchy is as follows:

    app_instances:
        - storage_instances:                 (1 or more per app_instance)
            + acl_policy                     (1 or more host initiators )
            + iqn                            (target IQN)
            + ips                            (target IPs)
            + volumes:                       (1 or more per storage_instance)
                * name
                * size
                * replication
                * performance_policy         (i.e. QoS)
                * protection_policy          (i.e. Snapshot schedules)


## Endpoints

HTTP operations on URL endpoints is the only way to interact with the set of managed objects.
URL's have the format:
```bash
      http://192.168.42.13:7717/v2.2/<object_class>/[<instance>]/...
```
where **7717** is the port used to access the API, and "v2.2" corresponds to an API version control.

Briefly, the REST API supports 4 operations/methods **create (POST), modify (PUT), list (GET), delete (DELETE)**.
Any input payload is in JSON format;  any return payload is in JSON format.
Login session keys are required within the "header" of any HTTP request.
Sessions keys have a 15 minute lifetime.

For a full reference documentation of the REST API, please review the Datera REST API Guide.

This Python SDK serves as a wrapper around the raw HTTP layer.

## Using this SDK

The Datera module is named **dfs_sdk**, and the main entry point is called __DateraApi__.
Obtaining an object handle can be done as follows:
```python
    from dfs_sdk import get_api
    [...]
    api = get_api(mgmt_ip, username, password, "v2.2" **kwargs)
```

You can also initialize the SDK using a Datera UDC file.  The following will read any valid
UDC file on the system or from the current environment variables.

```python
    from dfs_sdk.scaffold import get_api
    [...]
    api = get_api()
```
## Configurable Options

These options can be set on instantiation via the ``get_api`` constructor

Option | Default | Description
-------|-------- | -----------
tenant | '/root' | Datera account tenant/subtenant
timeout | 300 (s) | Timeout for HTTP requests
secure | True | Whether to use HTTPS (False sets HTTP)
strict | False | Whether to check if an endpoint is valid before sending request
cert | None | HTTPS verification certificate
cert\_key | None | HTTPS verification certificate key
thread\_local | {} | Used for passing values down to the connection layer, usually for logging


## Common Objects, Examples and  Use Cases

Please see the **utils** directory for programming examples that cover the following:

Common methods for all objects include **create(), set(), delete(), list()**

+ To create an app\_instance with name **FOO**:
```python
        ai = api.app_instances.create(name="FOO")
```
+ Looping through objects can be done via **list()**:
```python
        for ai in api.app_instances.list():
            print "AppInstance: ", ai
```
+ To set a given **app_instance** into an _offline_ state:
```python
        ai.set(admin_state="offline")
```
+ To delete a given app\_instance:
```python
        ai.delete()
```
## Reporting Problems

For problems and feedback, please email "support@datera.io"
