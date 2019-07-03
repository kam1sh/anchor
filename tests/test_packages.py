import pytest

from anchor import exceptions
from anchor.packages import models

from anchor.users.models import RoleType


@pytest.mark.unit
def test_reader(tempfile):
    """
    Checks that ChunkedReader max file size
    is working properly.
    """
    file = tempfile("file", size_kb=1024).open("rb")
    reader = models.ChunkedReader(file, max_size_kb=1025)
    assert reader.max_size == 1025 * 1024
    all(reader)


def test_new_file(packages):
    pkg = packages.new_package()
    file = packages.new_file(version="1.0.0rc2")
    assert pkg.owner == file.owner
    assert file.version


def test_keep(packages):
    pkg = packages.new_package()
    packages.new_file(version="1.0.0rc2")
    packages.new_file(version="1.0.0")
    retention = models.RetentionPolicy()
    retention.applied_to = pkg
    retention.keep(regexp=r"^\d+\.\d+\.\d+$")
    to_delete = retention.run(check=True)
    assert len(to_delete) == 1
    assert to_delete[0].version == "1.0.0rc2"


def test_owner_upload(packages, users):
    packages.new_file()
    user = users.new("test2@localhost")
    with pytest.raises(exceptions.Forbidden):
        packages.new_file(user=user, version="0.3.0")


def test_upload_permissions(packages, users):
    usr = users.new("test2@localhost")
    file = packages.new_file(version="0.1.0")
    package = file.package
    usr.give_access(package, role="developer")
    # usr.save()
    level = package.effective_level(usr)
    assert level == RoleType.developer
    assert package.permissions_for(level=level)
    assert not package.has_permission(usr, "remove_files")
    with pytest.raises(exceptions.Forbidden):
        packages.new_file(user=usr, version="0.1.0")
        pytest.fail("User reuploaded file")
    packages.new_file(user=usr, version="0.2.0")


def test_views(packages, client):
    file = packages.new_file(version="0.1.0")
    soup = client.get("/").soup
    assert not soup.find("a", href=""), "Package link broken"
    soup = client.get(file.package.detail_url()).soup
    sidebar = soup.find("nav", class_="nav-sidetabs")
    assert sidebar
    assert len(sidebar.find_all("a")) == 4
