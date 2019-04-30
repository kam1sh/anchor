from django.urls import path

from . import views

urlpatterns = [
    path("upload/", views.upload_package),
    path("simple/", views.PackageList.as_view()),
    path("simple/<str:name>/", views.files, name="pypi.files"),
]
