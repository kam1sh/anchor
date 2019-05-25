from ..packages import services
from .models import PackageFile, Project, ShaReader


class PyUploader(services.Uploader):
    pkg = Project
    pkg_file = PackageFile
    reader = ShaReader

    def get_reader(self):
        reader = super().get_reader()
        reader.hash = self.metadata.sha256_digest
        return reader


upload_file = PyUploader(__name__)
