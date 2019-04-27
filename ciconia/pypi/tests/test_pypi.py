from pathlib import Path

import pytest

from ciconia.pypi import models

WHEEL = Path("dist/ciconia-0.1.0-py3-none-any.whl")
TAR = Path("dist/ciconia-0.1.0.tar.gz")

@pytest.mark.parametrize("dist", [WHEEL, TAR], ids=lambda x: x.name)
def test_readers(dist):
    """ Tests for package reading (wheel and tar.gz) """
    fd = dist.open("rb")
    pkg = models.PackageFile(fd)
    assert pkg.filename == dist.name
    assert pkg.metadata
    # print(pkg.metadata["description"])

    assert models.WheelMetadata.fromkeys(pkg.metadata)
