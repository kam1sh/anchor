class ServiceError(Exception):
    """Basic anchor exception"""

    status_code = 500


class UserError(ServiceError):
    status_code = 400
