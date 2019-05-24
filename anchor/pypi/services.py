from ..packages import services
from .models import PackageFile, Project

upload_file = services.Uploader(Project, PackageFile, __name__)
