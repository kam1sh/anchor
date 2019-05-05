from django.contrib import admin

from .models import PackageFile, Project


class FilesInline(admin.TabularInline):
    model = PackageFile
    fields = ["filename", "sha256"]


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    model = Project
    inlines = [FilesInline]
    list_display = ["name", "version", "summary"]
