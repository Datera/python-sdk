#!/usr/bin/env python
from __future__ import (print_function, unicode_literals, division,
                        absolute_import)

"""
DO NOT USE

This is a WIP script to generate driver-specific configuration files from
a valid UDC config setup.

The original intention was to provide a way to get existing drivers that have
ecosystem-specific configuration files UDC support via generating those unique
configuration files from the config on the local machine.

Currently only the Datera Cinder driver is implemented (though a bit wonky
still).  Other candidates would be the Glance Store driver and the CSI plugin
yaml files.
"""

import re
import io
import os
import sys
from dfs_sdk import scaffold

CINDER_ETC_SECTION_RE = re.compile(r"^\[[Dd]atera\]\s*$")
GLANCE_STORE_RE = re.compile(r"^\[glance_store\]\s*$")


def _cinder_fix_enabled_backends(lines, index):
    line = lines[index]
    v = line.split('=')[-1]
    parts = v.split(',')
    parts.append('datera')
    newline = 'enabled_backends = {}'.format(','.join(parts))
    lines[index] = newline


def _cinder_add_enabled_backends(lines, index):
    lines.insert(index, 'enabled_backends = datera')


def _cinder_fix_default_volume_type(lines, index):
    lines[index] = 'default_volume_type = datera'


def _cinder_add_default_volume_type(lines, index):
    lines.insert(index, 'default_volume_type = datera')


def _cinder_fix_debug(lines, index):
    lines[index] = 'debug = True'


def _cinder_add_debug(lines, index):
    lines.insert(index, 'debug = True')


def _cinder_add_san(lines, index, conf):
    lines.insert(index+1, 'san_ip = {}'.format(conf['mgmt_ip']))


def _cinder_fix_san(lines, index, conf):
    lines[index] = 'san_ip = {}'.format(conf['mgmt_ip'])


def _cinder_add_user(lines, index, conf):
    lines.insert(index+1, 'san_login = {}'.format(conf['username']))


def _cinder_fix_user(lines, index, conf):
    lines[index] = 'san_login = {}'.format(conf['username'])


def _cinder_add_pass(lines, index, conf):
    lines.insert(index+1, 'san_password = {}'.format(conf['password']))


def _cinder_fix_pass(lines, index, conf):
    lines[index] = 'san_password = {}'.format(conf['password'])


def _cinder_add_vbn(lines, index):
    lines.insert(index+1, 'volume_backend_name = datera')


def _cinder_fix_vbn(lines, index):
    lines[index] = 'volume_backend_name = datera'


def _cinder_add_datera_debug(lines, index):
    lines.insert(index+1, 'datera_debug = True')


def _cinder_fix_datera_debug(lines, index):
    lines[index] = 'datera_debug = True'


def _cinder_add_tenant(lines, index, conf):
    lines.insert(index+1, 'datera_tenant_id = {}'.format(conf['tenant']))


def _cinder_fix_tenant(lines, index, conf):
    lines[index] = 'datera_tenant_id = {}'.format(conf['tenant'])


def _discover_section(lines, etcfile, name):
    start = None
    end = None
    matcher = re.compile(r"^\[{}\]\s*$".format(name))
    for i, line in enumerate(lines):
        if matcher.match(line):
            start = i
            break
    if start is None:
        raise EnvironmentError(
            "[DEFAULT] section missing from etcfile: {}".format(etcfile))
    end = start
    section_match = re.compile(r"^\[.*\]")
    for i, line in enumerate(lines[start+1:]):
        if section_match.match(line):
            break
        end += 1
    return start, end


def cinder_volume(conf, etcfile, inplace):
    if not os.path.isfile(etcfile):
        raise EnvironmentError(
            "cinder-volume etcfile not found at: {}".format(etcfile))
    lines = None
    with io.open(etcfile, 'r') as f:
        lines = [elem.strip() for elem in f.readlines()]

    # Handle [DEFAULT] section
    default_start, default_end = _discover_section(lines, etcfile, "DEFAULT")
    enabled_backends = None
    default_volume_type = None
    debug = None
    for i, line in enumerate(lines[default_start:default_end+1]):
        if line.startswith("enabled_backends"):
            enabled_backends = default_start + i
        if line.startswith("default_volume_type"):
            default_volume_type = default_start + i
        if line.startswith("debug"):
            debug = default_start + i

    if enabled_backends and "datera" not in lines[enabled_backends]:
        _cinder_fix_enabled_backends(lines, enabled_backends)
    elif not enabled_backends:
        _cinder_add_enabled_backends(lines, default_end)
    if default_volume_type and "datera" not in lines[default_volume_type]:
        _cinder_fix_default_volume_type(lines, default_volume_type)
    elif not default_volume_type:
        _cinder_add_default_volume_type(lines, default_end)
    if debug and 'True' not in lines[debug]:
        _cinder_fix_debug(lines, debug)
    elif not debug:
        _cinder_add_debug(lines, default_end)

    # Handle [datera] section
    dsection_start, dsection_end = _discover_section(lines, etcfile, "datera")
    if not dsection_start:
        raise EnvironmentError(
            "[datera] section missing from /etc/cinder/cinder.conf")

    san_check = 0
    user_check = 0
    pass_check = 0
    vbn_check = 0
    debug_check = 0
    tenant_check = 0

    for i, line in enumerate(lines[dsection_start:dsection_end+1]):
        if 'san_ip' in line:
            san_check = dsection_start + i
        if 'san_login' in line:
            user_check = dsection_start + i
        if 'san_password' in line:
            pass_check = dsection_start + i
        if 'volume_backend_name' in line:
            vbn_check = dsection_start + i
        if 'datera_debug ' in line:
            debug_check = dsection_start + i
        if 'datera_tenant_id' in line:
            tenant_check = dsection_start + i

    if not san_check:
        _cinder_add_san(lines, dsection_end, conf)
    else:
        _cinder_fix_san(lines, san_check, conf)

    if not user_check:
        _cinder_add_user(lines, dsection_end, conf)
    else:
        _cinder_fix_user(lines, user_check, conf)

    if not pass_check:
        _cinder_add_pass(lines, dsection_end, conf)
    else:
        _cinder_fix_pass(lines, pass_check, conf)

    if not vbn_check:
        _cinder_add_vbn(lines, dsection_end)
    else:
        _cinder_fix_vbn(lines, vbn_check)

    if not debug_check:
        _cinder_add_datera_debug(lines, dsection_end)
    else:
        _cinder_fix_datera_debug(lines, debug_check)

    if not tenant_check:
        _cinder_add_tenant(lines, dsection_end, conf)
    else:
        _cinder_fix_tenant(lines, tenant_check, conf)

    data = '\n'.join(lines)
    if inplace:
        with io.open(etcfile, 'w+') as f:
            f.write(data)
    else:
        print(data)


def glance_store(conf, etcfile, inplace):
    lines = None
    with io.open(etcfile, 'r') as f:
        lines = [elem.strip() for elem in f.readlines()]

    default_start, default_end = _discover_section(lines, etcfile, "DEFAULT")

    gs_start, gs_end = _discover_section(lines, etcfile, "glance_store")

    data = '\n'.join(lines)
    if inplace:
        with io.open(etcfile, 'w+') as f:
            f.write(data)


def main(args):
    scaffold.get_api()
    conf = scaffold.get_config()
    print("Using Config:")
    scaffold.print_config()
    if args.cinder_volume:
        cinder_volume(conf, args.cinder_volume, args.in_place)


if __name__ == "__main__":
    parser = scaffold.get_argparser()
    parser.add_argument('--in-place')
    parser.add_argument('--cinder-volume',
                        help='cinder.conf file to modify and add UDC '
                             'information')
    parser.add_argument('--glance',
                        help='glance-api.conf file to modify and add UDC '
                             'information')
    args = parser.parse_args()

    main(args)
    sys.exit(0)
