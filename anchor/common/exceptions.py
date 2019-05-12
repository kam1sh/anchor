class ServiceError(Exception):
    """Basic Ciconia exception"""

    status_code = 500


class UserError(ServiceError):
    status_code = 400
