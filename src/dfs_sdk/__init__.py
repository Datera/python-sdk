"""
Python package for interacting with the REST interface of a Datera
storage cluster.
"""
from __future__ import (print_function, absolute_import, unicode_literals,
                        division)

import os
# Renaming imports to prevent easy top-level importing
# We want folks to use get_api(), not these object directly
from .api import DateraApi as _DateraApi
from .api import DateraApi21 as _DateraApi21
from .api import DateraApi22 as _DateraApi22
from .api import DateraApi23 as _DateraApi23

from .constants import API_VERSIONS, DEFAULT_CACHED_SCHEMA
from .exceptions import ApiError
from .exceptions import ApiAuthError
from .exceptions import ApiInvalidRequestError
from .exceptions import ApiNotFoundError
from .exceptions import ApiConflictError
from .exceptions import ApiConnectionError
from .exceptions import ApiTimeoutError
from .exceptions import ApiInternalError
from .exceptions import ApiUnavailableError
from .dlogging import setup_logging
from .hooks.base import load_hooks


__copyright__ = "Copyright 2017, Datera, Inc."


# TODO(mss): generate this from version list imported from constants
VERSION_MAP = {"v2": _DateraApi,
               "v2.1": _DateraApi21,
               "v2.2": _DateraApi22,
               "v2.3": _DateraApi23}


def get_api(hostname, username, password, version, tenant=None, strict=True,
            hooks=None, refresh=False, **kwargs):
    """Main entrypoint into the SDK

    Returns a DateraApi object
    Parameters:
      hostname (str) - The hostname or VIP
      username (str) - e.g. "admin"
      password (str)
      version (str) - must be in constants.API_VERSIONS
    Optional parameters:
      tenant (str) - Tenant, for v2.1+ API only
      strict (bool) - Force all requests to use HTTPS (default True)
      hooks (list) - List of hook instances use (see dfs_sdk/hooks/base.py)
      refresh (bool) - Re-generate .cached-schema file from /api endpoint
    kwargs:
      extra_headers (dict) - Headers to pass along with all requests
      ldap_server (string) - LDAP server
      timeout (float) - HTTP connection  timeout.  If None, use system
                        default.
      secure (boolean) - Use HTTPS instead of HTTP, defaults to HTTPS
      thread_local (dict) - Thread local dictionary with trace id
      ldap_server (string) - LDAP server
      retry_503_type (string) - "backoff" or "random"
      retry_connection_type (string) - "backoff" or "random"
      immediate_login (bool) - Login to Datera cluster when object is returned
      verify (bool) - Verify HTTPS connection (
                      currently unsupported by Datera cluster)
    """
    setup_logging(kwargs.pop('disable_log', False))
    schema_loc = kwargs.get('schema_loc', DEFAULT_CACHED_SCHEMA)
    if version not in API_VERSIONS:
        raise NotImplementedError(
            "API version {} unsupported by SDK at this time. Supported "
            "versions: {}".format(version, API_VERSIONS))
    if version == "v2" and tenant:
        raise ValueError("API version v2 does not support multi-tenancy")
    api = VERSION_MAP[version](hostname,
                               username=username,
                               password=password,
                               tenant=tenant,
                               strict=strict,
                               **kwargs)
    if hooks:
        load_hooks(api, hooks)
    if refresh:
        try:
            os.remove(schema_loc)
        except OSError:
            pass
    return api


__all__ = ['get_api',
           'ApiError',
           'ApiAuthError',
           'ApiInvalidRequestError',
           'ApiNotFoundError',
           'ApiConflictError',
           'ApiConnectionError',
           'ApiTimeoutError',
           'ApiInternalError',
           'ApiUnavailableError']
