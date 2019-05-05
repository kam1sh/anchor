from django.urls import path

from . import views

urlpatterns = [
    path("", views.xmlrpc_dispatch),
    path("upload/", views.upload_package),
    path("simple/", views.list_packages),
    path("simple/<str:name>/", views.list_files, name="pypi.files"),
    path("download/<str:filename>", views.download_file, name="pypi.download"),
]
