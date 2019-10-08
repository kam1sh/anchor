from django.urls import path

from . import views
from ..packages import views as pkg_views

urlpatterns = [
    path("", views.xmlrpc_dispatch),
    path("upload/", views.upload_package),
    path("simple/", views.list_projects),
    path("simple/<str:name>/", views.list_files, name="pypi.files"),
    path("download/<str:filename>", pkg_views.download_file, name="pypi.download"),
]
