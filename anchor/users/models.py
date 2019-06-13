from django.contrib.auth.models import AbstractUser
from django.db.models import CharField, EmailField
from django.urls import reverse
from django.utils.translation import ugettext_lazy as _


class User(AbstractUser):

    # First Name and Last Name do not cover name patterns
    # around the globe.
    name = CharField(_("Name of User"), blank=True, max_length=255)
    # redefined field to make it unique and not blank
    email = EmailField("email address", blank=False, unique=True)

    # authorization by email was described in documentation, though I don't like it =/
    USERNAME_FIELD = "email"
    # auth.E002
    REQUIRED_FIELDS = []  # type: ignore

    def get_absolute_url(self):
        return reverse("users:details", kwargs={"username": self.username})

    def __str__(self):
        return self.email
