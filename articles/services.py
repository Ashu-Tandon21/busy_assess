"""Article lifecycle and query logic.

Every status transition goes through one of the functions below, and every
one of them re-checks who is allowed to do it — this is the actual
enforcement point for goal #1 ("must be enforced on the server, not just
hidden in the interface"). Views call these, catch TransitionError, and
show its message; they never flip `article.status` themselves.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta

from django.db import transaction
from django.db.models import Count, Q, QuerySet
from django.db.models.functions import TruncWeek
from django.utils import timezone

from .models import Article, ArticleAlertDismissal, ArticleEvent

Status = Article.Status


class TransitionError(Exception):
    """Raised when a requested move is illegal — message is shown to the user."""


def _log(article, actor, event_type, *, old_status=None, new_status=None, note=None):
    return ArticleEvent.objects.create(
        article=article,
        event_type=event_type,
        old_status=old_status or "",
        new_status=new_status or "",
        actor=actor,
        note=note or "",
    )


def can_edit(article: Article, user) -> bool:
    if article.status == Status.PUBLISHED:
        return False
    if user.is_editor:
        return True
    return user.is_writer and article.author_id == user.id


@transaction.atomic
def create_article(*, title: str, body: str, section, author) -> Article:
    from sections.services import assignable_sections

    if not author.is_editor and not assignable_sections(author).filter(pk=section.pk).exists():
        raise TransitionError("You can only create articles in sections you are assigned to.")
    article = Article.objects.create(title=title, body=body, section=section, author=author)
    _log(article, author, ArticleEvent.EventType.CREATED, new_status=article.status)
    return article


@transaction.atomic
def edit_article(article: Article, *, title: str, body: str, editor) -> Article:
    if not can_edit(article, editor):
        if article.status == Status.PUBLISHED:
            raise TransitionError(
                "Published articles cannot be edited directly — open a new revision instead."
            )
        raise TransitionError("You can only edit your own articles.")

    content_changed = article.title != title or article.body != body
    article.title = title
    article.body = body

    if content_changed and article.status in (Status.APPROVED, Status.SCHEDULED):
        old_status = article.status
        article.status = Status.IN_REVIEW
        article.publish_at = None
        article.save(update_fields=["title", "body", "status", "publish_at", "updated_at"])
        _log(
            article,
            editor,
            ArticleEvent.EventType.STATUS_CHANGE,
            old_status=old_status,
            new_status=article.status,
            note="Content edited — sent back to review.",
        )
    else:
        article.save(update_fields=["title", "body", "updated_at"])
    return article


@transaction.atomic
def submit_for_review(article: Article, *, actor) -> Article:
    if article.status != Status.DRAFT:
        raise TransitionError("Only a Draft article can be submitted for review.")
    if not actor.is_editor and article.author_id != actor.id:
        raise TransitionError("Only the article's author can submit it for review.")
    old_status = article.status
    article.status = Status.IN_REVIEW
    article.save(update_fields=["status", "updated_at"])
    _log(article, actor, ArticleEvent.EventType.STATUS_CHANGE, old_status=old_status, new_status=article.status)
    return article


@transaction.atomic
def approve(article: Article, *, actor) -> Article:
    if not actor.is_editor:
        raise TransitionError("Only an editor can approve an article.")
    if article.status != Status.IN_REVIEW:
        raise TransitionError("Only an article In Review can be approved.")
    if article.author_id == actor.id:
        raise TransitionError("You cannot approve your own article.")
    old_status = article.status
    article.status = Status.APPROVED
    article.save(update_fields=["status", "updated_at"])
    _log(article, actor, ArticleEvent.EventType.STATUS_CHANGE, old_status=old_status, new_status=article.status)
    return article


@transaction.atomic
def schedule(article: Article, *, actor, publish_at) -> Article:
    if not actor.is_editor:
        raise TransitionError("Only an editor can schedule an article.")
    if article.status != Status.APPROVED:
        raise TransitionError("Only an Approved article can be scheduled.")
    if publish_at is None or publish_at <= timezone.now():
        raise TransitionError("Publish time must be in the future.")
    old_status = article.status
    article.status = Status.SCHEDULED
    article.publish_at = publish_at
    article.save(update_fields=["status", "publish_at", "updated_at"])
    _log(article, actor, ArticleEvent.EventType.STATUS_CHANGE, old_status=old_status, new_status=article.status)
    return article


@transaction.atomic
def publish(article: Article, *, actor) -> Article:
    if not actor.is_editor:
        raise TransitionError("Only an editor can publish an article.")
    if article.status not in (Status.APPROVED, Status.SCHEDULED):
        raise TransitionError("Only an Approved or Scheduled article can be published.")
    old_status = article.status
    article.status = Status.PUBLISHED
    if old_status == Status.APPROVED:
        article.publish_at = timezone.now()
    article.save(update_fields=["status", "publish_at", "updated_at"])
    _log(article, actor, ArticleEvent.EventType.STATUS_CHANGE, old_status=old_status, new_status=article.status)

    if article.revision_of_id:
        parent = article.revision_of
        parent.title = article.title
        parent.body = article.body
        parent.save(update_fields=["title", "body", "updated_at"])
        _log(
            parent,
            actor,
            ArticleEvent.EventType.REVISION_OPENED,
            note=f"Revision #{article.pk} was published and its content replaced this article's content.",
        )
    return article


@transaction.atomic
def unpublish(article: Article, *, actor) -> Article:
    if not actor.is_editor:
        raise TransitionError("Only an editor can unpublish an article.")
    if article.status not in (Status.SCHEDULED, Status.PUBLISHED):
        raise TransitionError("Only a Scheduled or Published article can be unpublished.")
    old_status = article.status
    article.status = Status.APPROVED
    article.save(update_fields=["status", "updated_at"])
    _log(article, actor, ArticleEvent.EventType.STATUS_CHANGE, old_status=old_status, new_status=article.status)
    return article


@transaction.atomic
def open_revision(article: Article, *, actor) -> Article:
    if article.status != Status.PUBLISHED:
        raise TransitionError("A new revision can only be opened from a Published article.")
    if not actor.is_editor and article.author_id != actor.id:
        raise TransitionError("Only the article's author (or an editor) can open a revision.")
    if article.revisions.exclude(status=Status.PUBLISHED).exists():
        raise TransitionError("This article already has a revision in progress.")
    revision = Article.objects.create(
        title=article.title,
        body=article.body,
        section=article.section,
        author=article.author,
        revision_of=article,
    )
    _log(revision, actor, ArticleEvent.EventType.CREATED, new_status=revision.status)
    _log(
        article,
        actor,
        ArticleEvent.EventType.REVISION_OPENED,
        note=f"Revision #{revision.pk} opened.",
    )
    return revision


@transaction.atomic
def add_comment(article: Article, *, actor, text: str) -> ArticleEvent:
    text = text.strip()
    if not text:
        raise TransitionError("Comment cannot be empty.")
    return _log(article, actor, ArticleEvent.EventType.COMMENT, note=text)


# --- Queries -----------------------------------------------------------


def visible_articles(user) -> QuerySet[Article]:
    if user.is_editor:
        return Article.objects.all()
    return Article.objects.filter(section__writers=user)


SORT_OPTIONS = {
    "updated": "-updated_at",
    "status": "status",
    "publish_time": "publish_at",
}


def search_articles(user, *, q="", section=None, status=None, author=None, sort="updated"):
    qs = visible_articles(user).select_related("section", "author")
    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(body__icontains=q))
    if section:
        qs = qs.filter(section_id=section)
    if status:
        qs = qs.filter(status=status)
    if author:
        qs = qs.filter(author_id=author)
    order = SORT_OPTIONS.get(sort, SORT_OPTIONS["updated"])
    return qs.order_by(order, "-pk")


def overdue_articles(user=None) -> QuerySet[Article]:
    """Scheduled articles whose publish time has passed and are still not Published.

    A dismissal only silences the *current* (article, publish_at) pair, so
    a rescheduled article that goes overdue again is not excluded by an old
    dismissal for a different publish_at (see ArticleAlertDismissal).
    """
    qs = Article.objects.filter(status=Status.SCHEDULED, publish_at__lt=timezone.now())
    if user is not None and not user.is_editor:
        qs = qs.filter(section__writers=user)
    dismissed_pairs = set(
        ArticleAlertDismissal.objects.filter(article__in=qs).values_list("article_id", "publish_at")
    )
    return [a for a in qs.select_related("section", "author") if (a.id, a.publish_at) not in dismissed_pairs]


@transaction.atomic
def dismiss_alert(article: Article, *, actor) -> ArticleAlertDismissal:
    if not actor.is_editor:
        raise TransitionError("Only an editor can dismiss an alert.")
    dismissal, _created = ArticleAlertDismissal.objects.get_or_create(
        article=article, publish_at=article.publish_at, defaults={"dismissed_by": actor}
    )
    return dismissal


# --- Bulk actions --------------------------------------------------------


@dataclass
class BulkResult:
    article: Article
    ok: bool
    message: str


def bulk_schedule(article_ids, *, actor, publish_at) -> list[BulkResult]:
    results = []
    for article in Article.objects.filter(pk__in=article_ids).select_related("section"):
        try:
            schedule(article, actor=actor, publish_at=publish_at)
            results.append(BulkResult(article, True, "Scheduled."))
        except TransitionError as exc:
            results.append(BulkResult(article, False, str(exc)))
    return results


def bulk_unpublish(article_ids, *, actor) -> list[BulkResult]:
    results = []
    for article in Article.objects.filter(pk__in=article_ids).select_related("section"):
        try:
            unpublish(article, actor=actor)
            results.append(BulkResult(article, True, "Unpublished."))
        except TransitionError as exc:
            results.append(BulkResult(article, False, str(exc)))
    return results


# --- Dashboard aggregates --------------------------------------------------


def week_bounds(dt=None):
    """Monday 00:00 to next Monday 00:00, in the active timezone, for dt's week."""
    dt = dt or timezone.localtime()
    start = (dt - timedelta(days=dt.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    return start, start + timedelta(days=7)


def dashboard_stats():
    now = timezone.now()
    week_start, week_end = week_bounds(now)

    in_review = Article.objects.filter(status=Status.IN_REVIEW).count()
    scheduled_this_week = Article.objects.filter(
        status=Status.SCHEDULED, publish_at__gte=week_start, publish_at__lt=week_end
    ).count()
    published_this_week = Article.objects.filter(
        status=Status.PUBLISHED, publish_at__gte=week_start, publish_at__lt=week_end
    ).count()
    open_drafts = Article.objects.filter(status=Status.DRAFT).count()

    raw_counts = dict(
        Article.objects.values_list("status").annotate(count=Count("id")).order_by()
    )
    by_status = [
        {"value": value, "label": label, "count": raw_counts.get(value, 0)}
        for value, label in Status.choices
    ]

    by_section = list(
        Article.objects.values("section__name")
        .annotate(count=Count("id"))
        .order_by("-count")
    )

    eight_weeks_ago, _ = week_bounds(now - timedelta(weeks=7))
    published_per_week_raw = {
        row["week"]: row["count"]
        for row in (
            Article.objects.filter(status=Status.PUBLISHED, publish_at__gte=eight_weeks_ago)
            .annotate(week=TruncWeek("publish_at"))
            .values("week")
            .annotate(count=Count("id"))
        )
    }
    published_per_week = []
    for i in range(8):
        week_start_i = eight_weeks_ago + timedelta(weeks=i)
        # TruncWeek uses the DB's week start (Monday, for the default locale).
        matched = next(
            (v for k, v in published_per_week_raw.items() if k and k.date() == week_start_i.date()),
            0,
        )
        published_per_week.append({"week": week_start_i.strftime("%b %d"), "count": matched})

    return {
        "in_review": in_review,
        "scheduled_this_week": scheduled_this_week,
        "published_this_week": published_this_week,
        "open_drafts": open_drafts,
        "by_status": by_status,
        "by_section": by_section,
        "published_per_week": published_per_week,
    }
