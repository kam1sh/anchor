from django.http import HttpResponse


class AnchorException(Exception):
    pass


class ServiceError(AnchorException):
    """Basic anchor exception"""

    status_code = 500

    def to_response(self, request=None) -> HttpResponse:
        """ Creates HTTP response from exception info. """
        return HttpResponse(str(self), status=self.status_code)


class UserError(ServiceError):
    status_code = 400


class Forbidden(ServiceError):
    status_code = 403


class LoginRedirect(AnchorException):
    pass
