from django.contrib import admin

from .models import PackageFile, PythonPackage


class FilesInline(admin.TabularInline):
    model = PackageFile
    fields = ["filename", "sha256"]


@admin.register(PythonPackage)
class PythonPackageAdmin(admin.ModelAdmin):
    model = PythonPackage
    inlines = [FilesInline]
    list_display = ["name", "version", "summary"]
