from django.utils.decorators import method_decorator
from django.views import generic


from .simple import upload_package, list_packages, list_files
from .xmlrpc import dispatch as xmlrpc_dispatch
