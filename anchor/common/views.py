"""
This package contains useful decorators for any django applications.
"""
import base64
import functools

from allauth.account.forms import LoginForm
from django.contrib import auth
from django.http import HttpResponse
from django.urls import reverse

from .. import exceptions

__all__ = ["basic_auth"]


def basic_auth(func):
    """Decorator that wraps view behind HTTP basic authorization."""
    if not callable(func):
        return _auth(func)

    @functools.wraps(func)
    def wrapper(request, *args, **kwargs):
        result = _auth(request)
        if result is None:
            return HttpResponse("No authentication form provided", status=401)
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
    login, password = base64.b64decode(header).decode().split(":")
    user = auth.authenticate(request, username=login, password=password)
    if not user:
        return False
    auth.login(request, user)
    return user
