from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q
from django.utils.translation import gettext_lazy as _

from sections.models import Section


class Article(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", _("Draft")
        IN_REVIEW = "in_review", _("In Review")
        APPROVED = "approved", _("Approved")
        SCHEDULED = "scheduled", _("Scheduled")
        PUBLISHED = "published", _("Published")

    title = models.CharField(max_length=255)
    body = models.TextField()
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="articles",
    )
    section = models.ForeignKey(
        Section,
        on_delete=models.PROTECT,
        related_name="articles",
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
        db_index=True,
    )
    publish_at = models.DateTimeField(null=True, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    revision_of = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="revisions",
    )

    class Meta:
        ordering = ["-updated_at", "-pk"]
        constraints = [
            models.CheckConstraint(
                condition=~Q(pk=F("revision_of")),
                name="articles_revision_of_cannot_point_to_self",
            ),
        ]

    def __str__(self) -> str:
        return self.title


class AppendOnlyQuerySet(models.QuerySet):
    def update(self, **kwargs):
        raise TypeError("ArticleEvent records are append-only and cannot be updated.")

    def delete(self):
        raise TypeError("ArticleEvent records are append-only and cannot be deleted.")


class ArticleEvent(models.Model):
    class EventType(models.TextChoices):
        CREATED = "created", _("Created")
        STATUS_CHANGE = "status_change", _("Status Change")
        REVISION_OPENED = "revision_opened", _("Revision Opened")
        COMMENT = "comment", _("Comment")

    article = models.ForeignKey(
        Article,
        on_delete=models.PROTECT,
        related_name="events",
    )
    event_type = models.CharField(
        max_length=32,
        choices=EventType.choices,
        db_index=True,
    )
    old_status = models.CharField(
        max_length=20,
        choices=Article.Status.choices,
        null=True,
        blank=True,
    )
    new_status = models.CharField(
        max_length=20,
        choices=Article.Status.choices,
        null=True,
        blank=True,
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="article_events",
    )
    note = models.TextField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    objects = AppendOnlyQuerySet.as_manager()

    class Meta:
        ordering = ["created_at", "pk"]

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise ValidationError(
                "ArticleEvent records are append-only and cannot be updated."
            )
        return super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise ValidationError("ArticleEvent records are append-only and cannot be deleted.")

    def __str__(self) -> str:
        return f"{self.article_id}:{self.event_type}"


class ArticleAlertDismissal(models.Model):
    article = models.ForeignKey(
        Article,
        on_delete=models.PROTECT,
        related_name="alert_dismissals",
    )
    publish_at = models.DateTimeField()
    dismissed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="dismissed_article_alerts",
        limit_choices_to={"role": "editor"},
    )
    dismissed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-dismissed_at", "-pk"]
        constraints = [
            models.UniqueConstraint(
                fields=["article", "publish_at"],
                name="articles_alert_dismissal_unique_article_publish_at",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.article_id}@{self.publish_at.isoformat()}"
