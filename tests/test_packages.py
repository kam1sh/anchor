import pytest

from anchor import exceptions
from anchor.packages.models import RetentionPolicy


def test_new_files(packages):
    pkg = packages.new_package()
    file = packages.new_file(version="1.0.0rc2")
    assert pkg.owner == file.owner
    assert file.version


def test_keep(packages):
    pkg = packages.new_package()
    packages.new_file(version="1.0.0rc2")
    packages.new_file(version="1.0.0")
    retention = RetentionPolicy()
    retention.applied_to = pkg
    retention.keep(regexp=r"^\d+\.\d+\.\d+$")
    to_delete = retention.run(check=True)
    assert len(to_delete) == 1
    assert to_delete[0].version == "1.0.0rc2"


def test_owner_upload(packages, users):
    packages.new_file()
    packages.new_file(version="0.2.0")
    user = users.new("test2@localhost")
    with pytest.raises(exceptions.Forbidden):
        packages.new_file(user=user, version="0.3.0")


def test_upload_permissions(packages, users):
    usr = users.new("test2@localhost")
    package = packages.new_file()
    package.package.give_access(usr, "add")
    usr.save()
    packages.new_file(user=usr, version="0.2.0")
    # assert upload(auth="test2@localhost:123", version="0.2.0") == 200
