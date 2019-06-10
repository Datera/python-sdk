import os

import mock
import pytest

from dfs_sdk import get_api
from dfs_sdk.connection import ApiConnection
from dfs_sdk.constants import DEFAULT_CACHED_SCHEMA
from dfs_sdk.context import ApiContext
from tests.utils import load_asset


@pytest.yield_fixture
def mock_api_21():
    try:
        api = get_api('1.1.1.1',
                      'admin',
                      'password',
                      version="v2.1",
                      tenant='test',
                      timeout=0.01,
                      immediate_login=False)
        http = mock.Mock()
        ctxt_mock = ApiContext()
        ctxt_mock.hostname = "testhost"
        ctxt_mock.version = "v2.1"
        ctxt_mock.username = "admin"
        ctxt_mock.password = "password"
        ctxt_mock.schema_loc = DEFAULT_CACHED_SCHEMA
        ctxt_mock._reader = mock.Mock()
        con = ApiConnection.from_context(ctxt_mock)
        resp_data = load_asset("api_endpoint_21.txt")
        http.side_effect = [({"key": "84c457eb414c4ab5a472292c4bc2b1c1",
                              "version": "v2.1"}, 200, "", {}),
                            (resp_data, 200, "", {}),
                            ({"sw_version": "3.2.0.0"}, 200, "", {})]
        con._http_connect_request = http
        ctxt_mock.connection = con
        ctxt_mock.reader._ep_name_set.__contains__ = lambda a, b: True
        api.context = ctxt_mock
        yield api, http
    finally:
        try:
            os.remove(DEFAULT_CACHED_SCHEMA)
        except OSError:
            pass


@pytest.yield_fixture
def mock_api_22():
    try:
        api = get_api('1.1.1.1',
                      'admin',
                      'password',
                      version="v2.2",
                      tenant='test',
                      timeout=0.01,
                      immediate_login=False)
        http = mock.Mock()
        ctxt_mock = ApiContext()
        ctxt_mock.hostname = "testhost"
        ctxt_mock.version = "v2.2"
        ctxt_mock.username = "admin"
        ctxt_mock.password = "password"
        ctxt_mock._reader = mock.Mock()
        con = ApiConnection(ctxt_mock)
        resp_data = load_asset("api_endpoint_21.txt")
        http.side_effect = [({"key": "84c457eb414c4ab5a472292c4bc2b1c1",
                              "version": "v2.2"}, 200, "", {}),
                            (resp_data, 200, "", {})]
        con._http_connect_request = http
        ctxt_mock.connection = con
        ctxt_mock.reader._ep_name_set.__contains__ = lambda a, b: True
        api.context = ctxt_mock
        yield api, http
    finally:
        try:
            os.remove(DEFAULT_CACHED_SCHEMA)
        except OSError:
            pass
