"""
This package contains useful decorators for any django applications.
"""
import base64
import functools

from django.http import HttpResponse, HttpResponseBadRequest
from django.http import HttpResponseForbidden as forbidden
from django.contrib import auth


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
            return HttpResponseBadRequest(str(e))

    return wrapper


def basic_auth(func):
    """Decorator that wraps view behind HTTP basic authorization."""
    if not callable(func):
        return _auth(func)

    @functools.wraps(func)
    def wrapper(request, *args, **kwargs):
        result = _auth(request)
        if result is None:
            return HttpResponse("No authentication form provided", status=401)
            # return forbidden("Authentication form not provided")
        if not result:
            return HttpResponse("Invalid credentials", status=401)
        return func(request, *args, **kwargs)

    return wrapper


def _auth(request):
    """
    Tries to authorize the user.
    Returns:
      - None if no credentials found
      - False if credentials are invalid
      - User object on success
    """
    header = request.META.get("HTTP_AUTHORIZATION")
    if not header:
        return None
    header = header.split()[1]
    email, password = base64.b64decode(header).decode().split(":")
    user = auth.authenticate(request, email=email, password=password)
    if not user:
        return False
    auth.login(request, user)
    return user