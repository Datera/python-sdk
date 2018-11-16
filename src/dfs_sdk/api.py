"""
Provides the DateraApi objects
"""
import threading

from .constants import DEFAULT_HTTP_TIMEOUT, VERSION
from .connection import ApiConnection
from .context import ApiContext
from .base import Endpoint as _Endpoint

__copyright__ = "Copyright 2017, Datera, Inc."


DEFAULT_API_VERSION = "v2.1"


# Wrapper function to help deduplicate all the code we were getting with the
# different api versions with little to no difference in this class
def _api_getter(base):

    class _DateraBaseApi(base):
        """
        Use this object to talk to the REST interface of a Datera cluster
        """

        def __init__(self, hostname, username=None, password=None, **kwargs):
            """
            Parameters:
              hostname (str) - IP address or host name
              username (str) - Username to log in with, e.g. "admin"
              password (str) - Password to use when logging in to the cluster
              tenant (str) - Tenant, or None
              timeout (float) - HTTP connection  timeout.  If None, use system
                                default.
              secure (boolean) - Use HTTPS instead of HTTP, defaults to HTTPS
              thread_local (dict) - Thread local dictionary with trace id
              ldap_server (string) - LDAP server
              extra_headers (dict) - Headers to pass along with all requests
            """
            assert self._version is not None

            if not hostname or not username or not password:
                raise ValueError(
                    "hostname, username, and password are required")

            # Create the context object, common to all endpoints and entities:
            kwargs['hostname'] = hostname
            kwargs['username'] = username
            kwargs['password'] = password
            self._kwargs = kwargs
            self.context = self._create_context(**kwargs)
            super(_DateraBaseApi, self).__init__(self.context, None)

        @staticmethod
        def _create_context(hostname=None,
                            username=None,
                            password=None,
                            tenant=None,
                            timeout=DEFAULT_HTTP_TIMEOUT,
                            secure=True,
                            version=DEFAULT_API_VERSION,
                            strict=True,
                            cert=None,
                            cert_key=None,
                            thread_local=threading.local(),
                            remote_server=None,
                            ldap_server=None,
                            extra_headers=None,
                            retry_503_type=None,
                            immediate_login=True):
            """
            Creates the context object
            This will be attached as a private attribute to all entities
            and endpoints returned by this API.

            Note that this is responsible for creating a connection object,
            which is an attribute of the context object.
            """
            context = ApiContext()
            context.version = version

            context.hostname = hostname
            context.username = username
            context.password = password
            context.tenant = tenant

            context.timeout = timeout
            context.secure = secure
            context.strict = strict
            context.cert = cert
            context.cert_key = cert_key
            context.extra_headers = extra_headers
            if not extra_headers:
                context.extra_headers = {
                    'Datera-Driver': 'Python-SDK-{}'.format(VERSION)}
            context.thread_local = thread_local
            lds = remote_server
            if not lds:
                lds = ldap_server
            context.ldap_server = lds
            context.retry_503_type = retry_503_type
            context.connection = ApiConnection.from_context(context)
            # Support both ways of specifying ldap server
            if immediate_login:
                context.connection.login(
                    name=username,
                    password=password,
                    ldap_server=lds)
            return context

    return _DateraBaseApi


class RootEp(_Endpoint):
    """
    Top-level endoint, the starting point for all API requests
    """
    _name = ""

    def __init__(self, *args):
        super(RootEp, self).__init__(*args)


class DateraApi(_api_getter(RootEp)):

    _version = 'v2'

    def __init__(self, *args, **kwargs):
        super(DateraApi, self).__init__(*args, **kwargs)


class DateraApi21(_api_getter(RootEp)):

    _version = 'v2.1'

    def __init__(self, *args, **kwargs):
        super(DateraApi21, self).__init__(*args, **kwargs)


class DateraApi22(_api_getter(RootEp)):

    _version = 'v2.2'

    def __init__(self, *args, **kwargs):
        super(DateraApi22, self).__init__(*args, **kwargs)
