from django.test import Client as django_client

__all__ = ["Client"]


class Client(django_client):
    """
    Wrapper around django test client with a few extensions.
    """

    def request(self, **request):
        response = super().request(**request)
        return Response(response)


class Response:
    """
    Wrapper around HttpResponse with a few extra methods.
    """

    def __init__(self, response):
        self.orig = response

    def __getattr__(self, name):
        return getattr(self.orig, name)

    def __eq__(self, other):
        """
        Status code asserting:
        >>> assert resp == 200
        """
        if isinstance(other, int):
            return self.status_code == other
        return self.orig == other

    def __repr__(self):
        return "{}({})".format(self.__class__.__name__, self.status_code)

    def __str__(self):
        return str(self.orig)


def to_dataclass(data: dict, cls: type):
    """Converts dict to dataclass."""
    data = {k: v for k, v in data.items() if k in cls.__annotations__}
    return cls(**data)
