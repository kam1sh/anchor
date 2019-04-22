from django.db import models

# Create your models here.

class PythonPackage(models.Model):
    name = models.CharField(max_length=64)
    version = models.CharField('Latest version', max_length=16)
