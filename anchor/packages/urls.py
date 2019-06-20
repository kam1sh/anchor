from django.urls import path

from . import views

app_name = "packages"

urlpatterns = [
    path("<int:id>/", views.PackageDetail.as_view(), name="details"),
    # path("<int:id>/files")
]
