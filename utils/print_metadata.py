#!/usr/bin/env python
from __future__ import (print_function, unicode_literals, division,
                        absolute_import)

"""
Super simple script to dump the metadata for all app_instances.

Usage:
    $ ./print_metadata.py
"""

import sys

from dfs_sdk import scaffold


def main(args):
    api = scaffold.get_api()
    # config = scaffold.get_config()
    for ai in api.app_instances.list():
        print(ai.metadata.get())
    return 0


if __name__ == "__main__":
    parser = scaffold.get_argparser()
    args = parser.parse_args()

    main(args)
    sys.exit(0)
