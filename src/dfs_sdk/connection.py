"""
Provides the ApiConnection class
"""
import copy
import functools
import io
import json
import os
import random
import threading
import time
import urllib3
import uuid

import requests

from .dat_jank import post_to_get
from .exceptions import ApiError
from .exceptions import ApiAuthError, ApiConnectionError, ApiTimeoutError
from .exceptions import ApiInternalError, ApiNotFoundError
from .exceptions import ApiInvalidRequestError, ApiConflictError
from .exceptions import Api503RetryError, ApiValidationFailedError
from .constants import REST_PORT, REST_PORT_HTTPS
from .constants import VERSION, RETRY_TIMEOUT
from .dlogging import get_log
from .schema.reader import get_reader

__copyright__ = "Copyright 2017, Datera, Inc."

LOG = get_log(__name__)

# TODO(_alastor_): Add certificate verification
urllib3.disable_warnings()


def _version_to_int(ver):
    # Using a factor of 100 per digit so up to 100 versions are supported
    # per major/minor/patch/subpatch digit in this calculation
    # Example:
    # In [2]: _version_to_int("3.3.0.0")
    # Out[2]: 303000000
    # In [3]: _version_to_int("2.2.7.1")
    # Out[3]: 202070100
    VERSION_DIGITS = 4
    factor = pow(10, VERSION_DIGITS * 2)
    div = pow(10, 2)
    val = 0
    for c in ver.split("."):
        val += int(int(c) * factor)
        factor /= div
    return val


def dat_version_gte(version_a, version_b):
    return _version_to_int(version_a) >= _version_to_int(version_b)


def _with_authentication(method):
    """
    Decorator to wrap Api method calls so that we login again if our key
    expires.
    """
    @functools.wraps(method)
    def wrapper_method(self, *args, **kwargs):
        """ Call the original method with a re-login if needed """
        # if we haven't logged in yet, log in and then try the method:
        if not self._logged_in:
            LOG.debug("Log in to API...")
            self.login()
            return method(self, *copy.deepcopy(args), **copy.deepcopy(kwargs))
        # already logged in, but retry if needed in case the key expires:
        args_copy = copy.deepcopy(args)
        kwargs_copy = copy.deepcopy(kwargs)
        try:
            return method(self, *args, **kwargs)
        except ApiAuthError as e:
            if e.message == ('The key provided with the request does not '
                             'correspond to a valid session.'):
                LOG.debug("API auth error, so try to log in again...")
            else:
                LOG.warn("API auth error, so try to log in again...")
            self.login()
            return method(self, *args_copy, **kwargs_copy)
    return wrapper_method


def _with_retry(method):
    """
    Decorator to wrap Api method calls so we retry on 503 errors
    """
    @functools.wraps(method)
    def _wrapper_retry(self, *args, **kwargs):
        """ Call the original method with backoff """
        tstart = time.time()
        backoff = 1
        err = None
        no_response = False
        while time.time() - tstart < RETRY_TIMEOUT:
            try:
                # if len(args) > 0 and args[0].lower() == "post":
                #     method(self, *copy.deepcopy(args),
                #            **copy.deepcopy(kwargs))
                #     if not no_response:
                #         raise ApiConnectionError("BadStatusLineWhatever")
                #     if no_response:
                #         raise ApiConflictError("Ruh-Roh")
                return method(
                    self, *copy.deepcopy(args), **copy.deepcopy(kwargs))
            except Api503RetryError as e:
                no_response = False
                if self._context.retry_503_type == "random":
                    err = e
                    slp = round(random.random() * 10, 2)
                    LOG.warn("Hit 503 Retry.  "
                             "Adding random sleep and trying again in "
                             "{}s".format(slp))
                    time.sleep(slp)
                elif self._context.retry_503_type == "backoff":
                    err = e
                    LOG.warn("Hit 503 Retry.  "
                             "Backing off and trying again in {}s".format(backoff))
                    time.sleep(backoff)
                    backoff += 1
                else:
                    raise
            except ApiConnectionError as e:
                no_response = True
                if self._context.retry_connection_type == "random":
                    err = e
                    slp = round(random.random() * 10, 2)
                    LOG.warn("Hit Connection Error: {} Backing off and trying "
                             "again in {}s".format(e, slp))
                    time.sleep(slp)
                elif self._context.retry_connection_type == "backoff":
                    err = e
                    LOG.warn("Hit Connection Error: {} Backing off and trying "
                             "again in {}s".format(e, backoff))
                    time.sleep(backoff)
                    backoff += 1
                else:
                    raise
            except ApiConflictError as e:
                # ConflictError can only happen with POST requests
                if no_response:
                    return post_to_get(
                        self, method, args[1], kwargs['data'], e)
                raise
        raise ApiTimeoutError("Request never succeeded before timeout period "
                              "expired: {}".format(err))
    return _wrapper_retry


def _make_unicode_string(inval):
    """
    Converts a string or bytes into a UTF-8 unicode string
    """
    try:
        return unicode(inval, 'utf-8')  # Python2
    except NameError:
        return str(inval, 'utf-8')  # Python3


class ApiConnection(object):
    """
    This class wraps the HTTP connection, translates to/from JSON, and
    handles authentication.
    Its methods raise ApiError (or its subclasses) when things go wrong
    """
    HEADER_DATA = {'Datera-Driver': 'Python-SDK-{}'.format(VERSION)}

    def __init__(self, context):
        """
        Initialize a connection from a context object, which defines
        the hostname, username, password, etc.
        """
        self._context = context
        self._hostname = context.hostname
        self._username = context.username
        self._password = context.password
        self._tenant = context.tenant

        self._version = context.version
        self._cert = context.cert
        self._cert_key = context.cert_key

        self._secure = context.secure
        self._timeout = context.timeout
        self._ldap_server = context.ldap_server
        self._extra_headers = context.extra_headers
        self._verify = context.verify

        self._lock = threading.Lock()
        self._key = None
        self.reader = None
        self._logged_in = False
        self._product_version = None

    @classmethod
    def from_context(cls, context):
        return cls(context)

    def _get_request_attrs(self, urlpath):
        if self._secure:
            protocol = 'https'
            port = REST_PORT_HTTPS
            cert_data = ((self._cert, self._cert_key)
                         if self._cert_key else self._cert)
        else:
            protocol = 'http'
            port = REST_PORT
            cert_data = None
        api_version = self._version
        host = self._hostname
        connection_string = '{}://{}:{}/v{}/{}'.format(
                protocol, host, port, api_version.strip('v'),
                urlpath.strip('/'))
        return protocol, port, cert_data, api_version, host, connection_string

    def _http_connect_request(self, method, urlpath, headers=None, params=None,
                              body=None, files=None, sensitive=False):
        protocol, port, cert_data, api_version, host, connection_string = \
                self._get_request_attrs(urlpath)
        headers.update(**self._extra_headers)
        if headers['Datera-Driver'] != self.HEADER_DATA['Datera-Driver']:
            headers['Datera-Driver'] = "|".join((
                headers['Datera-Driver'], self.HEADER_DATA['Datera-Driver']))
        request_id = uuid.uuid4()
        if sensitive:
            dbody = "********"
            dheaders = "********"
        else:
            dbody = body
            dheaders = headers
        LOG.debug("\nDatera Trace ID: %(tid)s\n"
                  "Datera Request ID: %(rid)s\n"
                  "Datera Request URL: %(url)s\n"
                  "Datera Request Method: %(method)s\n"
                  "Datera Request Payload: %(payload)s\n"
                  "Datera Request Headers: %(header)s\n",
                  {'tid': getattr(
                      self._context.thread_local, 'trace_id', None),
                   'rid': request_id,
                   'url': connection_string,
                   'method': method,
                   'payload': dbody,
                   'header': dheaders})
        t1 = time.time()
        try:
            resp = getattr(requests, method.lower())(
                    connection_string, headers=headers, params=params,
                    data=body, verify=self._verify, files=files,
                    cert=cert_data)
            if sensitive or '/api' in resp.url:
                payload = "*********"
            else:
                payload = resp.content
            # Python 2/3 compatibility
            try:
                payload = payload.decode('utf-8').replace('\n', '')
            except AttributeError:
                payload = str(payload).replace('\n', '')
            t2 = time.time()
            timedelta = round(t2 - t1, 3)
            LOG.debug("\nDatera Trace ID: %(tid)s\n"
                      "Datera Response ID: %(rid)s\n"
                      "Datera Response TimeDelta: %(delta)ss\n"
                      "Datera Response URL: %(url)s\n"
                      "Datera Response Code: %(rcode)s\n"
                      "Datera Response Payload: %(payload)s\n"
                      "Datera Response Object: %(obj)s\n",
                      {'tid': getattr(
                          self._context.thread_local, 'trace_id', None),
                       'rid': request_id,
                       'delta': timedelta,
                       'url': resp.url,
                       'rcode': resp.status_code,
                       'payload': payload,
                       'obj': None})
        except requests.ConnectionError as e:
            raise ApiConnectionError(e, '')
        except requests.Timeout as e:
            raise ApiTimeoutError(e, '')
        if files:
            resp_data = {}
        else:
            resp_data = resp.json()
        resp_status = resp.status_code
        resp_reason = resp.reason
        resp_headers = resp.headers
        self._assert_response_successful(
            method, urlpath, body, resp_data, resp_status, resp_reason)
        return (resp_data, resp_status, resp_reason, resp_headers)

    def _get_schema(self, endpoint):
        """
        Tries to access cached schema, if not available, pulls new schema
        from the remote box.
        """
        data = None
        if os.path.exists(self._context.schema_loc):
            with io.open(self._context.schema_loc, 'rb') as f:
                fdata = f.read()
                data = {}
                if fdata:
                    try:
                        # Python 2.7
                        data = json.loads(fdata)
                    except TypeError:
                        # Python 3+
                        data = json.loads(fdata.decode('utf-8'))
                if self._version in data:
                    return data[self._version]
                # Making it sensitive so it doesn't clog the logs
                data[self._version] = self.read_endpoint(endpoint,
                                                         sensitive=True)
        else:
            # Making it sensitive so it doesn't clog the logs
            data = {self._version: self.read_endpoint(endpoint,
                                                      sensitive=True)}
        with io.open(self._context.schema_loc, 'wb+') as f:
            jdata = json.dumps(data)
            try:
                # Python 2.7
                f.write(jdata)
            except TypeError:
                # Python 3+
                f.write(jdata.encode('utf-8'))
        return data[self._version]

    @_with_retry
    def login(self, **params):
        """ Login to the API, store the key, get schema """
        if params:
            if params.get("ldap_server"):
                send_data = {"name": params.get("name"),
                             "password": params.get("password"),
                             "remote_server": params.get("ldap_server")}
            else:
                send_data = {"name": params.get("name"),
                             "password": params.get("password")}
        else:
            send_data = {"name": self._username, "password": self._password}
            if self._ldap_server:
                send_data.update({'remote_server': self._ldap_server})

        body = json.dumps(send_data)

        headers = {}
        headers["content-type"] = "application/json; charset=utf-8"
        urlpath = "/login"
        method = "PUT"
        with self._lock:
            resp_dict, resp_status, resp_reason, resp_hdrs = \
                self._http_connect_request(method, urlpath, body=body,
                                           headers=headers, sensitive=True)
            if 'key' not in resp_dict or not resp_dict['key']:
                raise ApiAuthError("No auth key returned", resp_dict)
            key = str(resp_dict['key'])
            self._key = key
            self._logged_in = True
            Reader = get_reader(self._version)
            reader = Reader(self._get_schema(Reader._endpoint))
            self.reader = reader
            system = self.read_entity("/system")
            self._product_version = system["sw_version"]

    def logout(self):
        """ Perform logout operation with the key"""
        with self._lock:
            key = self._key
            self._key = None
            self._logged_in = False
        headers = dict()
        headers["content-type"] = "application/json; charset=utf-8"
        headers["auth-token"] = key
        urlpath = "/logout"
        method = "PUT"
        self._http_connect_request(method, urlpath, headers=headers)

    @property
    def auth_key(self):
        return self._key

    @auth_key.setter
    def auth_key(self, new_key):
        self._key = new_key

    def _assert_response_successful(self, method, urlpath, body,
                                    resp_data, resp_status, resp_reason):
        """
        Raises an exception if the response was an error
          resp_data (str)
          resp_status (str)
          resp_reason (str)
        """
        if resp_status >= 200 and resp_status <= 299:
            return
        msg = "[REQUEST]: " + method + " " + urlpath + "\n"
        if body is not None:
            msg += str(body) + "\n"
        if resp_data:
            msg += '[RESPONSE]:\n'
            msg += str(resp_data) + "\n"
        msg += str(resp_status) + " " + str(resp_reason)
        if resp_status == 401:
            raise ApiAuthError(msg, resp_data)
        elif resp_status == 404:
            raise ApiNotFoundError(msg, resp_data)
        elif resp_status == 400 or resp_status == 405 or \
                resp_status == 403:
            raise ApiInvalidRequestError(msg, resp_data)
        elif resp_status == 422:
            raise ApiValidationFailedError(msg, resp_data)
        elif resp_status == 409:
            raise ApiConflictError(msg, resp_data)
        elif resp_status == 500:
            if 'REST server is still initializing' in resp_data.get(
                    'message', ''):
                raise Api503RetryError(msg, resp_data)
            raise ApiInternalError(msg, resp_data)
        elif resp_status == 503:
            raise Api503RetryError(msg, resp_data)
        else:
            raise ApiError(msg, resp_data)

    def _do_request(self, method, urlpath, files=None, data=None, params=None,
                    **kwargs):
        """
        Handle the aggregation of different pages for the request
        """
        resp_meta, resp_data = \
            self._do_auth_request(method, urlpath, data=data, params=params,
                                  files=files, **kwargs)

        # No metadata means no pagination
        if "metadata" not in resp_meta:
            return resp_meta, resp_data

        if "offset" in resp_meta["metadata"]:
            offset = resp_meta["metadata"]["offset"]
        else:
            offset = 0

        if params is None:
            params = {}

        # hotfix for issue with filter not being applied before
        # calculating total_count.  We're assuming that if
        # 'filter' is applied, we'll never have more than
        # 100 results which should account for the vast majority
        # of cases anyways.
        # This is fixed in the latest 3.3 patch
        filter_skip = False
        if "filter" in params and not dat_version_gte(
                self._product_version, "3.3.0.0"):
            filter_skip = True

        # Should we handle POST or PUT?
        # Limiting the method to GET for now
        if (method == "GET" and "total_count" in resp_meta["metadata"] and
                "request_count" in resp_meta["metadata"] and not filter_skip):
            # Keep firing until we get everything
            while True:
                ccount = offset + resp_meta["metadata"]["request_count"]
                tcount = resp_meta["metadata"]["total_count"]
                limit = params.get("limit", tcount) if params else tcount
                # If we've hit the limit or there isn't a limit parameter in
                # the returned metadata, we're done
                if limit <= ccount or "limit" not in resp_meta["metadata"]:
                    break

                offset += resp_meta["metadata"]["limit"]
                next_offset = {"offset": offset}
                params.update(next_offset)
                resp_meta, resp_data_container = \
                    self._do_auth_request(
                        method, urlpath, data, params=params)
                # Expanding the result
                if isinstance(resp_data, dict):
                    resp_data.update(resp_data_container)
                else:
                    resp_data.extend(resp_data_container)
        return resp_meta, resp_data

    def _build_body_headers(self, data=None, files=None, params=None,
                            **kwargs):
        headers = {}
        # tenant header
        if self._version == 'v2':
            pass  # v2 did not support multi-tenancy
        else:
            if self._tenant:
                headers["tenant"] = self._tenant
            else:
                headers["tenant"] = '/root'
            if isinstance(data, dict):
                if 'tenant' in data:
                    headers["tenant"] = data['tenant']
                    data.pop('tenant')
                elif 'data' in data:
                    if 'tenant' in data['data']:
                        headers["tenant"] = data['data']['tenant']
                        data['data'].pop('tenant')
            elif isinstance(params, dict):
                if 'tenant' in params:
                    headers["tenant"] = params['tenant']
                    params.pop('tenant')
        # Auth-Token header
        if self._key:
            headers["Auth-Token"] = self._key
        if not files:
            # content-type header
            headers["content-type"] = "application/json; charset=utf-8"
        if data is None:
            body = None
        elif isinstance(data, str):
            body = data
        elif files is not None:
            # Requests can't push a string and a file at the same time, so we
            # just pass the data as a normal python dict
            body = data
        else:
            body = json.dumps(data)
        return body, headers

    @_with_retry
    @_with_authentication
    def _do_auth_request(self, method, urlpath, files=None, data=None,
                         params=None, **kwargs):
        """
        Translates to/from JSON as needed, calls _http_connect_request()
        Bubbles up ApiError on error
        """
        sensitive = kwargs.get('sensitive')
        body, headers = self._build_body_headers(
            data=data, params=params, files=files)
        parsed_data, resp_status, resp_reason, _resp_headers = \
            self._http_connect_request(method, urlpath, params=params,
                                       body=body, headers=headers, files=files,
                                       sensitive=sensitive)

        ret_metadata = {}
        ret_data = parsed_data
        if self._version == 'v2':
            # v2 had no metadata
            ret_data = parsed_data
            ret_metadata = {}
        else:
            if isinstance(parsed_data, dict) and 'data' in parsed_data:
                ret_data = parsed_data.pop('data')
                ret_metadata = parsed_data
        return ret_metadata, ret_data

    @_with_retry
    @_with_authentication
    def _do_stream_request(self, urlpath, data=None, params=None, **kwargs):
        body, headers = self._build_body_headers(data=data, params=params)
        try:
            while True:
                parsed_data, resp_status, resp_reason, resp_headers = \
                    self._http_connect_request(
                        "GET", urlpath, params=params, body=body,
                        headers=headers, **kwargs)
                ret_data = parsed_data.pop('data')
                ret_metadata = parsed_data
                yield ret_metadata, ret_data
        except KeyboardInterrupt:
            LOG.debug("Ctrl-C recieved, ending stream")
    ########################################

    def create_entity(self, path, data, sensitive=False):
        """
        Returns the parsed response data
        Raises ApiError on error
        Parameters:
          path (str) - Endpoint path, e.g. "/app_templates"
          data (dict) - e.g. {"name": "myapptemplate"}
        """
        _metadata, data = self._do_request("POST", path, data=data,
                                           sensitive=sensitive)
        return data

    def read_endpoint(self, path, params=None, sensitive=False):
        """
        Returns the parsed response data
        Raises ApiError on error
        Parameters:
          path (str) - Endpoint path, e.g. "/app_templates"
          params (dict) - Querry Params, e.g. "/app_templates?key=value"
        """
        _metadata, data = self._do_request("GET", path, params=params,
                                           sensitive=sensitive)
        if 'complete' in _metadata:
            if not _metadata['complete']:
                return None
        return data

    def read_entity(self, path, params=None, sensitive=False):
        """
        Returns the parsed response data
        Raises ApiError on error
        Parameters:
          path (str) - Entity path, e.g. "/app_templates/myapptemplate"
          params (dict) - Querry Params, e.g. "/app_templates?key=value"
        """
        _metadata, data = self._do_request("GET", path, params=params,
                                           sensitive=sensitive)
        return data

    def update_endpoint(self, path, data, sensitive=False):
        """
        Returns the parsed response data
        Raises ApiError on error
        Parameters:
          path (str) - Endpoint path
          data (dict)
        """
        _metadata, data = self._do_request("PUT", path, data=data,
                                           sensitive=sensitive)
        return data

    def update_entity(self, path, data, sensitive=False):
        """
        Returns the parsed response data
        Raises ApiError on error
        Parameters:
          path (str) - Entity path, e.g. "/app_templates/myapptemplate"
          data (dict)
        """
        _metadata, data = self._do_request("PUT", path, data=data,
                                           sensitive=sensitive)
        return data

    def upload_endpoint(self, path, files, data, sensitive=False):
        """
        Returns the parsed response data
        Raises ApiError on error
        Parameters:
          path (str) - Entity path, e.g. "/app_templates/myapptemplate"
          data (dict)
          files (list)
          sensitive (boolean)
        """
        _metadata, data = self._do_request("PUT", path, data=data,
                                           files=files, sensitive=sensitive)
        return data

    def stream_endpoint(self, path, data, interval, timeout):
        """
        Streams Endpoint Data
        Raises ApiError on error
        Parameters:
          path (str) - Entity path, e.g. "/app_templates/myapptemplate"
          data (dict)
        """
        if timeout == 0:
            timeout = "inf"
        try:
            for _metadata, data in self._do_stream_request(path, data=data):
                yield _metadata, data
                time.sleep(interval)
                if timeout != "inf":
                    timeout -= interval
                    if timeout <= 0:
                        LOG.debug("Timeout reached, ending stream")
                        return
        except KeyboardInterrupt:
            LOG.debug("Ctrl-C recieved, ending stream")

    def delete_entity(self, path, data=None, sensitive=False):
        """
        Returns the parsed response data
        Raises ApiError on HTTP error
        Parameters:
          path (str) - Entity path, e.g. "/app_templates/myapptemplate"
        """
        _metadata, data = self._do_request("DELETE", path, data=data,
                                           sensitive=sensitive)
        return data
