#!/usr/bin/env python
from __future__ import (print_function, unicode_literals, division,
                        absolute_import)

"""
Simple script to create a bunch of AppInstances with similar names.  This
has been replaced by DBMP, but the script can still be useful for one-off
creations.


Usage:
    $ ./make_ais.py --prefix my-vol --number 10

    $ ./make_ais.py --prefix test \
         --size 5 \
         --number 200 \
         --threads 20 \
         --replica_count 2
"""

import sys
import threading
try:
    from Queue import Queue
except ImportError:
    from queue import Queue

from dfs_sdk import scaffold


def _worker(api, queue):
    while not queue.empty():
        name, size, replica_count = queue.get()
        print("Creating AppInstance:", name)
        ai = api.app_instances.create(name=name)
        si = ai.storage_instances.create(name="storage-1")
        si.volumes.create(name="volume-1", size=size,
                          replica_count=replica_count)
        queue.task_done()


def main(args):
    api = scaffold.get_api()

    # Populate Queue
    ai_names = Queue()
    for i in range(args.number):
        name = "-".join((args.prefix, str(i)))
        ai_names.put((name, args.size, args.replica_count))

    for _ in range(args.threads):
        thread = threading.Thread(target=_worker,
                                  args=(api, ai_names))
        thread.daemon = True
        thread.start()

    ai_names.join()


if __name__ == "__main__":
    parser = scaffold.get_argparser()
    parser.add_argument("-n", "--number", default=5, type=int,
                        help="Number of AppInstances")
    parser.add_argument("-s", "--size", default=1, type=int,
                        help="Size of AppInstances")
    parser.add_argument("-p", "--prefix", default="my-app",
                        help="Prefix each AppInstance should use")
    parser.add_argument("-r", "--replica-count", default=3, type=int,
                        help="Number of replicas for volumes, default: 3")
    parser.add_argument("-m", "--threads", default=5, type=int,
                        help="Threads to use for deletion")
    args = parser.parse_args()

    main(args)
    sys.exit(0)
