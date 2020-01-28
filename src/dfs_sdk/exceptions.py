"""
Provides exceptions classes
"""
import json

from .dlogging import get_log

LOG = get_log(__name__)

__copyright__ = "Copyright 2017, Datera, Inc."


class SdkError(Exception):
    """ This is the base class for SDK exceptions

    Exceptions specifically dealing with the SDK should inherit from the class

    Exceptions dealing with API responses should use exceptions that inherit
    from ApiResponseError
    """
    pass


class ApiError(Exception):
    """ This is the base class for exceptions raised by the API """
    pass


###############################################################################


class ApiConnectionError(ApiError):
    """ Error trying to communicate with the server """
    pass


class ApiTimeoutError(ApiConnectionError):
    """ Timeout waiting for a response """
    pass


###############################################################################


class _ApiResponseError(ApiError):
    """
    This is the base class for exceptions raised due to an error returned
    by the REST server.

    The JSON response payload is made available as exception attributes
    """
    message = None
    code = None
    http = None
    name = None

    def __init__(self, msg, resp_data=None):
        super(_ApiResponseError, self).__init__(msg)
        self.msg = msg
        self.resp_data = resp_data or '{}'
        js = {}
        if isinstance(self.resp_data, dict):
            js = self.resp_data
        else:
            try:
                js = json.loads(self.resp_data)
            except ValueError:
                LOG.error("Invalid json payload from API response!")
            except TypeError as e:
                LOG.error("Object recieved from API response was unexpected "
                          "type error: {}, data: {}".format(e, self.resp_data))

        for attr in js.keys():
            # Intentionally overwrite exp.message since it's deprecated
            # str(exp) will use exp.args instead of exp.message
            if attr == 'message' or getattr(self, attr, None) is None:
                setattr(self, attr, js[attr])


class ApiAuthError(_ApiResponseError):
    """ Error due to wrong username/password """
    pass


class ApiInternalError(_ApiResponseError):
    """ HTTP 500 """
    pass


class ApiUnavailableError(_ApiResponseError):
    """
    Error indicating the API version request is not available on this system
    """
    pass


class ApiInvalidRequestError(_ApiResponseError):
    """ Incorrect parameters or URL """
    pass


class ApiValidationFailedError(ApiInvalidRequestError):
    """ Request failed validation, see message attribute for reason """
    pass


class ApiNotFoundError(_ApiResponseError):
    """ HTTP 404 Not Found """
    pass


class ApiConflictError(_ApiResponseError):
    """ Edit conflict """
    pass


class Api503RetryError(_ApiResponseError):
    """ The system is overloaded, retry in a bit """


###############################################################################

class SdkTypeNotFound(SdkError):
    """ Generic SDK type not found exception """
    pass


class SdkEndpointNotFound(SdkTypeNotFound):
    """ SDK Endpoint type was not found """
    pass


class SdkEntityNotFound(SdkTypeNotFound):
    """ SDK Entity type was not found """
    pass
