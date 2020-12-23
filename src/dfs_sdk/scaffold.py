from __future__ import (print_function, unicode_literals, division,
                        absolute_import)

import argparse
import copy
import io
import json
import os
import pprint
import re
import sys

from dfs_sdk import get_api as _get_api

IPRE_STR = r'(\d{1,3}\.){3}\d{1,3}'
IPRE = re.compile(IPRE_STR)

SIP = re.compile(r'san_ip\s+?=\s+?(?P<san_ip>%s)' % IPRE_STR)
SLG = re.compile(r'san_login\s+?=\s+?(?P<san_login>.*)')
SPW = re.compile(r'san_password\s+?=\s+?(?P<san_password>.*)')
TNT = re.compile(r'datera_tenant_id\s+?=\s+?(?P<tenant_id>.*)')
LDP = re.compile(r'datera_ldap_server\s+?=\s+?(?P<ldap>.*)')

LATEST = "2.3"
FALLBACK = ["2", "2.1", "2.2"]

UNIX_HOME = os.path.join(os.path.expanduser('~'))
UNIX_CONFIG_HOME = os.path.join(UNIX_HOME, 'datera')
UNIX_SITE_CONFIG_HOME = '/etc/datera'
CONFIG_SEARCH_PATH = [os.getcwd(), UNIX_HOME, UNIX_CONFIG_HOME,
                      UNIX_SITE_CONFIG_HOME]
CONFIGS = [".datera-config", "datera-config", ".datera-config.json",
           "datera-config.json"]
CINDER_ETC = "/etc/cinder/cinder.conf"

REPLACE_IP = "REPLACE_ME_WITH_REAL_IP_OR_HOSTNAME"
EXAMPLE_CONFIG = {"mgmt_ip": REPLACE_IP,
                  "username": "admin",
                  "password": "password",
                  "tenant": "/root",
                  "api_version": "2.3",
                  "ldap": ""}
DATERA_RC = "datrc"

ENV_MGMT = "DAT_MGMT"
ENV_USER = "DAT_USER"
ENV_PASS = "DAT_PASS"
ENV_TENANT = "DAT_TENANT"
ENV_API = "DAT_API"
ENV_LDAP = "DAT_LDAP"

EXAMPLE_RC = """\
# DATERA ENVIRONMENT VARIABLES
{}=1.1.1.1
{}=admin
{}=password
{}=/root
{}=2.3
{}=
""".format(ENV_MGMT, ENV_USER, ENV_PASS, ENV_TENANT, ENV_API, ENV_LDAP)

ENV_HELP = {ENV_MGMT: "Datera management IP address or hostname",
            ENV_USER: "Datera account username",
            ENV_PASS: "Datera account password",
            ENV_TENANT: "Datera tenant ID. eg: SE-OpenStack",
            ENV_API: "Datera API version. eg: 2.3",
            ENV_LDAP: "Datera account LDAP server"}

_CONFIG = {}
_ARGS = None
VERBOSE = False


def _print_envs():
    print()
    print("DATERA ENVIRONMENT VARIABLES")
    print("============================")
    longest = 0
    for key in ENV_HELP:
        if len(key) > longest:
            longest = len(key)
    for key, help in sorted(ENV_HELP.items()):
        buff = " " * (longest - len(key))
        print("{}{} -- {}".format(buff, key, help))
    print()


def _gen_config():
    if _ARGS.gen_config == "json":
        if any((os.path.exists(c) for c in CONFIGS)):
            print("Config file already exists in current directory.  Please "
                  "move or remove it before generating a new one")
            sys.exit(1)
        with io.open(CONFIGS[-1], 'w+', encoding='utf-8') as f:
            # Python2 Compatibility
            try:
                f.write(unicode(json.dumps(
                    EXAMPLE_CONFIG, ensure_ascii=False, indent=4)))
            except NameError:
                json.dump(EXAMPLE_CONFIG, f, indent=4)
    elif _ARGS.gen_config == "shell":
        if os.path.exists(DATERA_RC):
            print("RC file already exists in current directory. Please move "
                  "or remove it before generating a new one")
            sys.exit(1)
        with io.open(DATERA_RC, 'w+') as f:
            f.write(EXAMPLE_RC)


def _search_config():
    for p in CONFIG_SEARCH_PATH:
        for conf in CONFIGS:
            fpath = os.path.join(p, conf)
            if os.path.exists(fpath):
                return fpath


def _check_config(config_file):
    missing = []
    for key in EXAMPLE_CONFIG:
        if key not in _CONFIG:
            missing.append(key)
    if missing:
        raise EnvironmentError(
            "All config options must be specified by config file, environment "
            "variable or CLI argument. Missing config keys: {}, config_file: "
            "{}".format(missing, config_file))


def _defaults():
    if not _CONFIG.get("tenant"):
        _CONFIG["tenant"] = "/root"
    if not _CONFIG.get("api_version"):
        _CONFIG["api_version"] = LATEST
    if not _CONFIG.get("ldap"):
        _CONFIG["ldap"] = ""


def _read_config(config_file):
    global _CONFIG
    if not config_file:
        if _ARGS and _ARGS.config:
            config_file = _ARGS.config
        else:
            config_file = _search_config()
            if not config_file:
                _CONFIG = _read_cinder_conf()
    if config_file:
        with io.open(config_file) as f:
            _CONFIG = json.loads(f.read())
    if _CONFIG is None:
        _CONFIG = {}
    _env_override()
    _cli_override()
    _defaults()
    _check_config(config_file)
    return config_file


def _read_cinder_conf():
    if not os.path.exists(CINDER_ETC):
        return
    data = None
    found_index = 0
    found_last_index = -1
    with io.open(CINDER_ETC) as f:
        for index, line in enumerate(f):
            if '[datera]' == line.strip().lower():
                found_index = index
                break
        for index, line in enumerate(f):
            if '[' in line and ']' in line:
                found_last_index = index + found_index
                break
    with io.open(CINDER_ETC) as f:
        data = "".join(f.readlines()[
            found_index:found_last_index])
    san_ip = SIP.search(data).group('san_ip')
    san_login = SLG.search(data).group('san_login')
    san_password = SPW.search(data).group('san_password')
    tenant = TNT.search(data)
    ldap = LDP.search(data)
    if tenant:
        tenant = tenant.group('tenant_id')
    else:
        tenant = "/root"
    if ldap:
        ldap = ldap.group('ldap')
    else:
        ldap = ""
    return {"mgmt_ip": san_ip,
            "username": san_login,
            "password": san_password,
            "tenant": tenant,
            "api_version": LATEST,
            "ldap": ldap}


def _cli_override():
    if _ARGS is None:
        return
    if _ARGS.hostname:
        _CONFIG["mgmt_ip"] = _ARGS.hostname
    if _ARGS.username:
        _CONFIG["username"] = _ARGS.username
    if _ARGS.password:
        _CONFIG["password"] = _ARGS.password
    if _ARGS.tenant:
        _CONFIG["tenant"] = _ARGS.tenant
    if _ARGS.api_version:
        _CONFIG["api_version"] = _ARGS.api_version
    if _ARGS.ldap:
        _CONFIG["ldap"] = _ARGS.ldap


def _env_override():
    if ENV_MGMT in os.environ:
        _CONFIG["mgmt_ip"] = os.environ[ENV_MGMT]
    if ENV_USER in os.environ:
        _CONFIG["username"] = os.environ[ENV_USER]
    if ENV_PASS in os.environ:
        _CONFIG["password"] = os.environ[ENV_PASS]
    if ENV_TENANT in os.environ:
        _CONFIG["tenant"] = os.environ[ENV_TENANT]
    if ENV_API in os.environ:
        _CONFIG["api_version"] = os.environ[ENV_API]
    if ENV_LDAP in os.environ:
        _CONFIG["ldap"] = os.environ[ENV_LDAP]


def vprint(*args, **kwargs):
    global VERBOSE
    if VERBOSE:
        print(*args, **kwargs)


def get_api(**kwargs):
    global _CONFIG
    if kwargs.pop('reset_config', False):
        _CONFIG = None
    udc_file = _read_config(kwargs.pop('config', None))
    tenant = _CONFIG["tenant"]
    if tenant and "root" not in tenant and tenant != "all":
        tenant = "/root/{}".format(tenant)
    if not tenant:
        tenant = "/root"
    if not _CONFIG["api_version"]:
        version = "v{}".format(LATEST)
    else:
        version = "v{}".format(_CONFIG["api_version"].strip("v"))
    # Check that mgmt_ip isn't the default
    if _CONFIG["mgmt_ip"] == REPLACE_IP:
        if not udc_file:
            udc_file = "none found"
        raise ValueError("You must edit your UDC config file [{}] and provide "
                         "at least the mgmt_ip of the Datera box you want to "
                         "connect to".format(udc_file))
    return _get_api(_CONFIG["mgmt_ip"],
                    username=_CONFIG["username"],
                    password=_CONFIG["password"],
                    version=version,
                    tenant=tenant,
                    remote_server=_CONFIG["ldap"],
                    **kwargs)


def print_config():
    config = copy.deepcopy(_CONFIG)
    config["password"] = "******"
    pprint.pprint(config)


def get_config(config_file=None, **kwargs):
    global _CONFIG
    if kwargs.get('reset_config'):
        _CONFIG = None
    if not _CONFIG:
        _read_config(config_file)
    return copy.deepcopy(_CONFIG)


def get_argparser(add_help=True):
    global _ARGS, VERBOSE
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--api-version",
                        help="Datera API version to use (default={})".format(
                            LATEST))
    parser.add_argument("--hostname", help="Hostname or IP Address of Datera "
                                           "backend")
    parser.add_argument("--username", help="Username for Datera account")
    parser.add_argument("--password", help="Password for Datera account")
    parser.add_argument("--tenant",
                        help="Tenant Name/ID to search under,"
                             " use 'all' for all tenants")
    parser.add_argument("--ldap", help="Datera LDAP authentication server")
    parser.add_argument("--config", help="Config file location")
    parser.add_argument("--print-envs", action="store_true",
                        help="Print supported environment variables")
    parser.add_argument("--gen-config", choices=["json", "shell"],
                        help="Generate example config")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Enable verbose output")
    args, _ = parser.parse_known_args()
    _ARGS = args
    VERBOSE = args.verbose
    if args.print_envs:
        _print_envs()
        sys.exit(0)
    if args.gen_config:
        _gen_config()
        sys.exit(0)
    return argparse.ArgumentParser(add_help=add_help, parents=[parser])
