"""
Module dedicated to workarounds that shouldn't be needed and should be removed
at the first opportunity
"""

import os

from .dlogging import get_log

LOG = get_log(__name__)


def post_to_get(self, method, path, data, e):
    LOG.warning(
        "Recieved ConflictError during no-response connection "
        " retry.  Assuming successful creation: {}".format(e))
    path = guess_resource_path(path, data)
    if not path:
        raise
    return method(self, "GET", path)


def guess_resource_path(url, data):
    resource_payload_identifier_keys = ['name', 'id', 'uuid']
    for key in resource_payload_identifier_keys:
        if key in data:
            return os.path.join(url, data[key])
    LOG.error(
        "Could not determine resource path from payload: {}".format(data))
