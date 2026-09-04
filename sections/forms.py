from django import forms

from accounts.models import User

from .models import Section


class SectionForm(forms.ModelForm):
    owning_editor = forms.ModelChoiceField(
        queryset=User.objects.filter(role=User.Role.EDITOR).order_by("email"),
    )

    class Meta:
        model = Section
        fields = ["name", "description", "owning_editor"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["owning_editor"].widget.attrs["class"] = "form-select"


class AssignWriterForm(forms.Form):
    writer = forms.ModelChoiceField(
        queryset=User.objects.filter(role=User.Role.WRITER).order_by("email"),
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    def __init__(self, *args, section=None, **kwargs):
        super().__init__(*args, **kwargs)
        if section is not None:
            already_assigned = section.writers.values_list("pk", flat=True)
            self.fields["writer"].queryset = self.fields["writer"].queryset.exclude(
                pk__in=already_assigned
            )
