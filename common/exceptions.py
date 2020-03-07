"""
Custom exceptions for our marshmallow
"""

from marshmallow_jsonapi.exceptions import IncorrectTypeError


class ForbiddenIdError(IncorrectTypeError):
    """
    Raised when a client attempts to provide an id when creating a resource. Special case so we can
    return the correct response code.
    """
    pointer = '/data/id'
    default_message = '`data` object must not include `id` key.'


class MismatchIdError(IncorrectTypeError):
    """
    Raised when a client provides an id that doesn't match the request. Special case so we can
    return the correct response code.
    """
    pointer = '/data/id'
    default_message = 'Mismatched id. Expected "{expected}".'


class NullPrimaryData(Exception):
    """ Raised by Schema.unwrap_request when the primary data object is null/None. """
    pass
