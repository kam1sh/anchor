from pathlib import Path
from ciconia.pypi import models

WHEEL = Path("dist/ciconia-0.1.0-py3-none-any.whl")


def test_wheel_reader():
    fd = WHEEL.open("rb")
    pkg = models.PackageFile(fd)
    assert pkg.filename == "ciconia-0.1.0-py3-none-any.whl"
    assert pkg.metadata
    print(pkg.metadata["description"])
