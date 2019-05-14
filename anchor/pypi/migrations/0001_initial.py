# Generated by Django 2.2.1 on 2019-05-14 17:23

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [("packages", "0001_initial")]

    operations = [
        migrations.CreateModel(
            name="Project",
            fields=[
                (
                    "package_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="packages.Package",
                    ),
                )
            ],
            bases=("packages.package",),
        ),
        migrations.CreateModel(
            name="PackageFile",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("filename", models.CharField(max_length=64, unique=True)),
                ("fileobj", models.FileField(upload_to="pypi")),
                ("pkg_type", models.CharField(max_length=16)),
                ("sha256", models.CharField(max_length=64, unique=True)),
                ("_metadata", models.TextField()),
                (
                    "project",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to="pypi.Project"
                    ),
                ),
            ],
        ),
    ]
