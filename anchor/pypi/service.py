import logging

from django.db import transaction

from .models import Metadata, Project, PackageFile

__all__ = ["new_package"]

log = logging.getLogger(__name__)


def new_package(metadata: dict, fd):
    """
    Creates new package and project records if necessary.
    """
    form = Metadata(metadata)

    # at first find the project to check permissions
    try:
        project = Project.objects.get(name=form.name)
        # TODO check permissions
    except Project.DoesNotExist:
        # automatically create new project
        project = Project()
    project.from_metadata(form)

    try:
        pkg_file = PackageFile.objects.get(filename=fd.name)
    except PackageFile.DoesNotExist:
        pkg_file = PackageFile()
    pkg_file.metadata = form
    pkg_file.update(fd)

    log.debug("Got package %s and project %s", pkg_file, project)

    with transaction.atomic():
        project.save()
        pkg_file.project = project
        pkg_file.save()
    return pkg_file
