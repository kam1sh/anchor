"""
This package contains useful decorators for any django applications.
"""
import functools

from django import http


def wrap_exceptions(method):
    """
    Catches standard exceptions and returns http responses with them.
    Example:
    ValueError -> Bad request
    """
    # TODO maybe rewrite to middleware?
    @functools.wraps(method)
    def wrapper(*args, **kwargs):
        try:
            return method(*args, **kwargs)
        except ValueError as e:
            return http.HttpResponseBadRequest(str(e))

    return wrapper
