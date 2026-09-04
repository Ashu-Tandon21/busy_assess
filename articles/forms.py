from django import forms
from django.utils import timezone

from sections.services import assignable_sections

from .models import Article


class ArticleForm(forms.ModelForm):
    class Meta:
        model = Article
        fields = ["title", "section", "body"]
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control"}),
            "section": forms.Select(attrs={"class": "form-select"}),
            "body": forms.Textarea(attrs={"class": "form-control", "rows": 14}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user is not None:
            self.fields["section"].queryset = assignable_sections(user)
        if self.instance.pk:
            # Section can't be changed once an article exists — only which
            # section it was *created* in is meaningful to the workflow.
            self.fields.pop("section")


class ScheduleForm(forms.Form):
    publish_at = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={"class": "form-control", "type": "datetime-local"}),
        label="Publish at",
    )

    def clean_publish_at(self):
        value = self.cleaned_data["publish_at"]
        if timezone.is_naive(value):
            value = timezone.make_aware(value)
        return value


class CommentForm(forms.Form):
    text = forms.CharField(
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 2, "placeholder": "Leave a comment…"}),
        label="",
    )


class BulkActionForm(forms.Form):
    ACTION_CHOICES = [("schedule", "Schedule"), ("unpublish", "Unpublish")]

    action = forms.ChoiceField(choices=ACTION_CHOICES)
    article_ids = forms.CharField(widget=forms.HiddenInput())
    publish_at = forms.DateTimeField(required=False)

    def clean_article_ids(self):
        raw = self.cleaned_data["article_ids"]
        try:
            ids = [int(x) for x in raw.split(",") if x]
        except ValueError:
            raise forms.ValidationError("Invalid selection.")
        if not ids:
            raise forms.ValidationError("Select at least one article.")
        return ids

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("action") == "schedule":
            publish_at = cleaned.get("publish_at")
            if not publish_at:
                self.add_error("publish_at", "Publish time is required to schedule.")
            elif timezone.is_naive(publish_at):
                cleaned["publish_at"] = timezone.make_aware(publish_at)
        return cleaned
