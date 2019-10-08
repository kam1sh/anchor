from django.urls import path

from . import views

app_name = "packages"

urlpatterns = [
    path("<int:id>/", views.PackageDetail.as_view(), name="details"),
    path("<int:id>/files", views.ListFiles.as_view(), name="files"),
    # path("<int:id>/settings", views.PermissionView)
    # path("<int:id>/permissions", views.PermissionView)
    path("files/<int:id>/rm", views.FileRemove.as_view(), name="files_rm"),
]
