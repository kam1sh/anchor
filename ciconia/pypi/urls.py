from django.urls import include, path
from django.views.generic import TemplateView

from . import views

urlpatterns = [
    path("", views.PackageList.as_view()),
    path("<str:name>/", views.PackageVersions.as_view())
]