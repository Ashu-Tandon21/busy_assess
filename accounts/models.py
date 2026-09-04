from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _


class User(AbstractUser):
    class Role(models.TextChoices):
        EDITOR = "editor", _("Editor")
        WRITER = "writer", _("Writer")

    email = models.EmailField(_("email address"), unique=True)
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.WRITER,
    )

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    def __str__(self) -> str:
        return self.email
