from django.urls import include, path
from django.views.generic import TemplateView

from .views import PackageList

urlpatterns = [
    path("", PackageList.as_view())
]