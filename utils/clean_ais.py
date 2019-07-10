#!/usr/bin/env python
from __future__ import (print_function, unicode_literals, division,
                        absolute_import)

"""
Simple helper script to clean AppInstances matching a regex filter

This has mostly been replaced by DBMP (github.com/Datera/dbmp)

Usage:
    $ ./clean_ais.py -f my-app --threads 10

    $ ./clean_ais.py --all --threads 10

    $ echo "my-app1\nmy-app2" | ./clean_ais.py --stdin
"""

import re
import sys
import threading
import time
try:
    from Queue import Queue
except ImportError:
    from queue import Queue

from builtins import input

from dfs_sdk import scaffold


def _add_worker(queue, to_delete, api, filters):
    while not queue.empty():
        tenant = queue.get()
        ais = api.app_instances.list(tenant=tenant)
        for ai in ais:
            if any((compf.match(ai['name']) for compf in filters)):
                to_delete.add((ai['name'], ai['path'], tenant))
        queue.task_done()


def _del_worker(queue, api):
    # Give time for the queue to fill
    time.sleep(0.2)
    while not queue.empty():
        _, path, tenant = queue.get()
        ai = api.app_instances.entity_from_path(path, tenant=tenant)
        print("Deleting: ", ai['name'])
        ai.set(admin_state="offline", force=True, tenant=tenant)
        ai.delete(tenant=tenant)
        queue.task_done()


def main(args):
    api = scaffold.get_api()
    config = scaffold.get_config()
    to_delete = set()

    filter_strs = set(args.re_filter)
    if args.stdin:
        for line in sys.stdin.readlines():
            filter_strs.add(line.strip())

    filters = []
    if args.all:
        filter_strs.add(".*")

    for f in filter_strs:
        filters.append(re.compile(f))

    tqueue = Queue()
    if config["tenant"] in ["all", "ALL"]:
        for tenant in api.tenants.list():
            tqueue.put(tenant['path'])
    else:
        tqueue.put(config["tenant"])

    for _ in range(args.threads):
        thread = threading.Thread(target=_add_worker,
                                  args=(tqueue, to_delete, api, filters))
        thread.daemon = True
        thread.start()

    tqueue.join()

    to_delete_queue = Queue()
    to_delete = sorted(to_delete)
    print("Using CONFIG:")
    scaffold.print_config()
    print("Delete These AppInstances from {}?".format(config["mgmt_ip"]))
    for ai in to_delete:
        to_delete_queue.put(ai)
        print(ai[0])

    yes = False
    if not args.yes and not args.stdin:
        yes = True if input("Y/n\n").strip() in ("Y", "yes") else False

    if args.stdin and len(filter_strs) > 1 and ".*" not in filter_strs:
        yes = True

    if yes or args.yes:
        for _ in range(args.threads):
            thread = threading.Thread(target=_del_worker,
                                      args=(to_delete_queue, api))
            thread.daemon = True
            thread.start()

        to_delete_queue.join()

    return 0


if __name__ == "__main__":
    parser = scaffold.get_argparser()
    parser.add_argument("-f", "--re-filter", action="append", default=[],
                        help="Regex filter to use when matching AppInstances")
    parser.add_argument("-a", "--all", action='store_true',
                        help="Match all AppInstances")
    parser.add_argument("-y", "--yes", action='store_true',
                        help="DANGER!!! Bypass confirmation prompt")
    parser.add_argument("-m", "--threads", default=5, type=int,
                        help="Threads to use for deletion")
    parser.add_argument("-s", "--stdin", action='store_true',
                        help="Takes STDIN input list and deletes matching AIs "
                             "THIS OPTION DOES NOT PROMPT FOR VERIFICATION. "
                             "You cannot specify '--all' when using stdin")
    args = parser.parse_args()

    main(args)
    sys.exit(0)
