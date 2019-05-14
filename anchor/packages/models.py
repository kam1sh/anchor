import enum

from django.utils import timezone
from django.db import models


class PackageTypes(enum.Enum):
    Python = "python"
    RPM = "rpm"
    DEB = "deb"
    Docker = "docker"


class Package(models.Model):
    pkg_type = models.CharField(
        max_length=16, db_index=True, choices=[(tag, tag.value) for tag in PackageTypes]
    )
    name = models.CharField(max_length=64, db_index=True)
    version = models.CharField("Latest version", max_length=16)
    summary = models.TextField(null=True)
    updated = models.DateTimeField("Last updated")
    # updated with the new package version
    info = models.TextField("Package information", null=True)

    def __init__(self, *args, metadata=None):
        super().__init__(*args)
        if metadata:
            self.from_metadata(metadata)

    def from_metadata(self, metadata):
        """ Updates package info from pkg_file metadata. """
        self.name = metadata.name
        self.version = metadata.version
        self.summary = metadata.summary
        self.info = metadata.description
        self.updated = timezone.now()

    def __str__(self):
        return self.name + " " + self.version
