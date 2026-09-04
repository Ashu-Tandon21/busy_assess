from django.conf import settings
from django.db import models


class Section(models.Model):
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    owning_editor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_sections",
        limit_choices_to={"role": "editor"},
    )
    writers = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through="SectionAssignment",
        related_name="assigned_sections",
    )
    is_archived = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name", "pk"]

    def __str__(self) -> str:
        return self.name


class SectionAssignment(models.Model):
    section = models.ForeignKey(
        Section,
        on_delete=models.CASCADE,
        related_name="assignments",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="section_assignments",
        limit_choices_to={"role": "writer"},
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["section", "user"],
                name="sections_assignment_unique_section_user",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.section} -> {self.user}"
