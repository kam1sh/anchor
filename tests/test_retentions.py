from anchor.packages.models import RetentionPolicy


def test_keep(packages):
    pkg = packages.new(name="package1", version="1.0.0")
    packages.new_file(version="1.0.0rc2")
    packages.new_file(version="1.0.0")
    retention = RetentionPolicy()
    retention.applied_to = pkg
    retention.keep(regexp=r"^\d+\.\d+\.\d+$")
    to_delete = retention.run(check=True)
    assert len(to_delete) == 1
    assert to_delete[0].version == "1.0.0rc2"
