import logging

from django.db import transaction

from .models import Metadata, PackageFile, Project
from ..common.exceptions import Forbidden

__all__ = ["new_package"]

log = logging.getLogger(__name__)


def new_package(user, form: Metadata, fd) -> PackageFile:
    """
    Creates new package and project records if necessary.
    """

    # at first find the project to check permissions
    # TODO use get_or_create()?
    try:
        project = Project.objects.get(name=form.name)
        if not project.available_to(user, "add"):
            raise Forbidden(f"You have no access to upload files in {project.name}")
    except Project.DoesNotExist:
        # automatically create new project
        project = Project()
        project.owner = user
    project.from_metadata(form)

    try:
        pkg_file = PackageFile.objects.get(filename=fd.name)
        if not pkg_file.available_to(user, "change"):
            raise Forbidden("You have no access to rewrite this file")
    except PackageFile.DoesNotExist:
        pkg_file = PackageFile()
        pkg_file.owner = user
    pkg_file.metadata = form
    pkg_file.update(fd)

    log.debug("Got package %s and project %s", pkg_file, project)

    with transaction.atomic():
        project.save()
        pkg_file.package = project
        pkg_file.save()
    return pkg_file
