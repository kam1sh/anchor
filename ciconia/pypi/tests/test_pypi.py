from pathlib import Path
import subprocess

import pytest

import ciconia
from ciconia.pypi import models

WHEEL = next(Path("dist").glob("*.whl"))
TAR = next(Path("dist").glob("*.tar.gz"))


def sha256sum(pth: Path):
    return subprocess.check_output(
        ["sha256sum", pth.absolute()], encoding="utf-8"
    ).split()[0]


@pytest.mark.parametrize("dist", [WHEEL, TAR], ids=["wheel", "tar"])
def test_readers(dist):
    """ Tests for package reading (wheel and tar.gz) """
    fd = dist.open("rb")
    pkg = models.PackageFile(pkg=fd)
    assert pkg.filename == dist.name
    assert pkg.fileobj.name == dist.name
    assert pkg.version == ciconia.__version__
    assert pkg.sha256 == sha256sum(dist)
    assert isinstance(pkg.metadata["requires-dist"], list)
