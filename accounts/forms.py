from django import forms
from django.contrib.auth.forms import UserCreationForm

from .models import User


class UserCreateForm(UserCreationForm):
    """Editor-facing account creation form.

    There's no public signup route — an editor fills this in to add a writer
    (or another editor) to the roster. Password fields/validation come from
    UserCreationForm; we just add the fields specific to this app's User model.
    """

    class Meta(UserCreationForm.Meta):
        model = User
        fields = ["username", "email", "role"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs["class"] = "form-control"
        self.fields["email"].widget.attrs["class"] = "form-control"
        self.fields["role"].widget.attrs["class"] = "form-select"
        self.fields["password1"].widget.attrs["class"] = "form-control"
        self.fields["password2"].widget.attrs["class"] = "form-control"