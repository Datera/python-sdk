#!/usr/bin/env python

from __future__ import (print_function, unicode_literals, division,
                        absolute_import)

import os
import re
import subprocess
import sys

import openstack

from dfs_sdk import scaffold
from dfs_sdk.scaffold import vprint

# Taken from this SO post :
# http://stackoverflow.com/a/18516125
# Using old-style string formatting because of the nature of the regex
# conflicting with new-style curly braces
UUID4_STR_RE = ("[a-f0-9]{8}-?[a-f0-9]{4}-?4[a-f0-9]{3}-?[89ab]"
                "[a-f0-9]{3}-?[a-f0-9]{12}")
UUID4_RE = re.compile(UUID4_STR_RE)
verbose = False


def usage():
    print("OS_USERNAME, OS_PASSWORD, OS_AUTH_URL and "
          "OS_PROJECT_NAME must be set")


def exe(cmd):
    vprint("Running cmd:", cmd)
    return subprocess.check_output(cmd, shell=True)


def main(args):

    api = scaffold.get_api()

    conn = openstack.connect()

    # Earlier versions of openstacksdk didn't let us filter by tenant
    # So multi-project accumulation has to be done via openstackclient
    if args.all_projects_all_tenants:
        # Get all openstack volume UUIDs
        ids = exe("openstack volume list --all-projects --format value | "
                  "awk '{print $1}'").split("\n")
        # Filter Nones
        vols = {vid for vid in ids if vid}

        # Get all openstack projects
        pids = exe("openstack project list --format value "
                   "| awk '{print $1}'").split("\n")

        # Iterate through projects and accumulate image ids
        imgids = []
        for pid in [p for p in pids if p]:
            try:
                imgids.extend(
                    exe("openstack --os-project-id {} image list --format "
                        "value | awk '{{print $1}}'".format(pid)).split("\n"))
            except subprocess.CalledProcessError:
                pass
        imgids = set(imgids)
        vols = vols.union(
                {imgid for imgid in imgids if imgid})

    else:
        vols = {str(vol.id) for vol in conn.block_storage.volumes()}
        vols = vols.union(
                {str(img.id) for img in conn.image.images()})

    yes_os, non_os = set(), set()
    ais = api.app_instances.list()
    for ai in ais:
        uid = UUID4_RE.search(ai['name'])
        if not uid or uid.group() not in vols:
            non_os.add(ai['name'])
        else:
            yes_os.add(ai['name'])

    pdisplay = "all" if args.all_projects_all_tenants else os.getenv(
        "OS_PROJECT_NAME")
    if args.only_os_orphans:
        for ai_name in sorted(non_os):
            if ai_name.startswith("OS-"):
                print(ai_name)
    else:
        print("OpenStack Project:", pdisplay)
        print("Datera Tenant: ", scaffold.get_config()["tenant"])
        print()
        print("Datera OpenStack AIs")
        print("--------------------")
        for ai_name in sorted(yes_os):
            print(ai_name)
        print("\nDatera Non-OpenStack AIs")
        print("------------------------")
        for ai_name in sorted(non_os):
            print(ai_name)


if __name__ == "__main__":

    parser = scaffold.get_argparser()
    parser.add_argument('--all-projects-all-tenants', action='store_true')
    parser.add_argument('--only-os-orphans', action='store_true')
    # parser.add_argument('--only-cached-images', action='store_true')
    args = parser.parse_args()
    sys.exit(main(args))
