from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import User
from sections.models import Section, SectionAssignment

from . import services
from .models import Article, ArticleAlertDismissal, ArticleEvent


def make_user(email, role):
    return User.objects.create_user(username=email.split("@")[0], email=email, password="pw12345", role=role)


class ArticleLifecycleTests(TestCase):
    """Every legal move, and the specific illegal ones the brief calls out."""

    def setUp(self):
        self.editor = make_user("editor@example.com", User.Role.EDITOR)
        self.other_editor = make_user("editor2@example.com", User.Role.EDITOR)
        self.writer = make_user("writer@example.com", User.Role.WRITER)
        self.other_writer = make_user("writer2@example.com", User.Role.WRITER)
        self.section = Section.objects.create(name="Politics", owning_editor=self.editor)
        SectionAssignment.objects.create(section=self.section, user=self.writer)
        SectionAssignment.objects.create(section=self.section, user=self.other_writer)

    def make_article(self, author=None):
        return services.create_article(
            title="Headline", body="Body text.", section=self.section, author=author or self.writer
        )

    # --- creation -----------------------------------------------------

    def test_writer_can_create_in_assigned_section(self):
        article = self.make_article()
        self.assertEqual(article.status, Article.Status.DRAFT)
        self.assertTrue(article.events.filter(event_type=ArticleEvent.EventType.CREATED).exists())

    def test_writer_cannot_create_in_unassigned_section(self):
        other_section = Section.objects.create(name="Tech", owning_editor=self.editor)
        with self.assertRaises(services.TransitionError):
            services.create_article(title="X", body="Y", section=other_section, author=self.writer)

    # --- submit ---------------------------------------------------------

    def test_author_can_submit_draft(self):
        article = self.make_article()
        services.submit_for_review(article, actor=self.writer)
        article.refresh_from_db()
        self.assertEqual(article.status, Article.Status.IN_REVIEW)

    def test_only_draft_can_be_submitted(self):
        article = self.make_article()
        services.submit_for_review(article, actor=self.writer)
        with self.assertRaises(services.TransitionError):
            services.submit_for_review(article, actor=self.writer)

    def test_other_writer_cannot_submit_someone_elses_draft(self):
        article = self.make_article()
        with self.assertRaises(services.TransitionError):
            services.submit_for_review(article, actor=self.other_writer)

    # --- approve --------------------------------------------------------

    def test_author_cannot_approve_own_article(self):
        article = self.make_article()
        services.submit_for_review(article, actor=self.writer)
        with self.assertRaises(services.TransitionError):
            services.approve(article, actor=self.writer)

    def test_a_different_editor_can_approve(self):
        article = self.make_article()
        services.submit_for_review(article, actor=self.writer)
        services.approve(article, actor=self.editor)
        article.refresh_from_db()
        self.assertEqual(article.status, Article.Status.APPROVED)

    def test_writer_cannot_approve_at_all(self):
        article = self.make_article()
        services.submit_for_review(article, actor=self.writer)
        with self.assertRaises(services.TransitionError):
            services.approve(article, actor=self.other_writer)

    def test_cannot_approve_a_draft(self):
        article = self.make_article()
        with self.assertRaises(services.TransitionError):
            services.approve(article, actor=self.editor)

    # --- schedule / publish / unpublish ---------------------------------

    def _approved_article(self):
        article = self.make_article()
        services.submit_for_review(article, actor=self.writer)
        services.approve(article, actor=self.editor)
        return article

    def test_schedule_requires_future_time(self):
        article = self._approved_article()
        with self.assertRaises(services.TransitionError):
            services.schedule(article, actor=self.editor, publish_at=timezone.now() - timedelta(hours=1))

    def test_schedule_then_publish_keeps_scheduled_time(self):
        article = self._approved_article()
        publish_at = timezone.now() + timedelta(days=1)
        services.schedule(article, actor=self.editor, publish_at=publish_at)
        services.publish(article, actor=self.editor)
        article.refresh_from_db()
        self.assertEqual(article.status, Article.Status.PUBLISHED)
        self.assertEqual(article.publish_at, publish_at)

    def test_publish_immediately_stamps_now(self):
        article = self._approved_article()
        before = timezone.now()
        services.publish(article, actor=self.editor)
        article.refresh_from_db()
        self.assertEqual(article.status, Article.Status.PUBLISHED)
        self.assertGreaterEqual(article.publish_at, before)

    def test_writer_cannot_schedule_or_publish(self):
        article = self._approved_article()
        with self.assertRaises(services.TransitionError):
            services.schedule(article, actor=self.writer, publish_at=timezone.now() + timedelta(days=1))
        with self.assertRaises(services.TransitionError):
            services.publish(article, actor=self.writer)

    def test_unpublish_from_scheduled_and_published_returns_to_approved(self):
        article = self._approved_article()
        services.publish(article, actor=self.editor)
        services.unpublish(article, actor=self.editor)
        article.refresh_from_db()
        self.assertEqual(article.status, Article.Status.APPROVED)

    def test_cannot_publish_an_in_review_article(self):
        article = self.make_article()
        services.submit_for_review(article, actor=self.writer)
        with self.assertRaises(services.TransitionError):
            services.publish(article, actor=self.editor)

    # --- editing sends back to review ------------------------------------

    def test_editing_approved_article_sends_back_to_review(self):
        article = self._approved_article()
        services.edit_article(article, title="New title", body="New body", editor=self.editor)
        article.refresh_from_db()
        self.assertEqual(article.status, Article.Status.IN_REVIEW)
        self.assertEqual(article.title, "New title")

    def test_editing_scheduled_article_sends_back_to_review(self):
        article = self._approved_article()
        services.schedule(article, actor=self.editor, publish_at=timezone.now() + timedelta(days=1))
        services.edit_article(article, title="New title", body="New body", editor=self.editor)
        article.refresh_from_db()
        self.assertEqual(article.status, Article.Status.IN_REVIEW)
        self.assertIsNone(article.publish_at)

    def test_published_article_cannot_be_edited_directly(self):
        article = self._approved_article()
        services.publish(article, actor=self.editor)
        with self.assertRaises(services.TransitionError):
            services.edit_article(article, title="New", body="New", editor=self.editor)

    def test_writer_cannot_edit_someone_elses_draft(self):
        article = self.make_article()
        with self.assertRaises(services.TransitionError):
            services.edit_article(article, title="X", body="Y", editor=self.other_writer)

    # --- revisions --------------------------------------------------------

    def test_revision_can_only_open_from_published(self):
        article = self._approved_article()
        with self.assertRaises(services.TransitionError):
            services.open_revision(article, actor=self.writer)

    def test_revision_opens_at_draft_and_links_to_parent(self):
        article = self._approved_article()
        services.publish(article, actor=self.editor)
        revision = services.open_revision(article, actor=self.writer)
        self.assertEqual(revision.status, Article.Status.DRAFT)
        self.assertEqual(revision.revision_of_id, article.pk)
        self.assertTrue(
            article.events.filter(event_type=ArticleEvent.EventType.REVISION_OPENED).exists()
        )

    def test_publishing_a_revision_replaces_parent_content(self):
        article = self._approved_article()
        services.publish(article, actor=self.editor)
        original_title = article.title

        revision = services.open_revision(article, actor=self.writer)
        revision.title = "Corrected headline"
        revision.body = "Corrected body."
        revision.save(update_fields=["title", "body"])
        services.submit_for_review(revision, actor=self.writer)
        services.approve(revision, actor=self.editor)
        services.publish(revision, actor=self.editor)

        article.refresh_from_db()
        self.assertEqual(article.title, "Corrected headline")
        self.assertNotEqual(article.title, original_title)
        # The parent's own status is untouched by the revision publishing.
        self.assertEqual(article.status, Article.Status.PUBLISHED)

    # --- comments / timeline ------------------------------------------------

    def test_comment_is_recorded_and_append_only(self):
        article = self.make_article()
        event = services.add_comment(article, actor=self.editor, text="Nice lede.")
        self.assertEqual(event.event_type, ArticleEvent.EventType.COMMENT)
        with self.assertRaises(Exception):
            event.note = "edited"
            event.save()
        with self.assertRaises(Exception):
            event.delete()

    def test_empty_comment_rejected(self):
        article = self.make_article()
        with self.assertRaises(services.TransitionError):
            services.add_comment(article, actor=self.editor, text="   ")


class BulkActionTests(TestCase):
    def setUp(self):
        self.editor = make_user("editor@example.com", User.Role.EDITOR)
        self.writer = make_user("writer@example.com", User.Role.WRITER)
        self.section = Section.objects.create(name="Politics", owning_editor=self.editor)
        SectionAssignment.objects.create(section=self.section, user=self.writer)

    def _article(self, status=Article.Status.APPROVED):
        article = services.create_article(
            title="A", body="B", section=self.section, author=self.writer
        )
        if status == Article.Status.DRAFT:
            return article
        services.submit_for_review(article, actor=self.writer)
        if status == Article.Status.IN_REVIEW:
            return article
        services.approve(article, actor=self.editor)
        return article

    def test_bulk_schedule_reports_per_article_success_and_failure(self):
        approved = self._article(Article.Status.APPROVED)
        still_in_review = self._article(Article.Status.IN_REVIEW)

        results = services.bulk_schedule(
            [approved.pk, still_in_review.pk],
            actor=self.editor,
            publish_at=timezone.now() + timedelta(days=1),
        )
        by_id = {r.article.pk: r for r in results}
        self.assertTrue(by_id[approved.pk].ok)
        self.assertFalse(by_id[still_in_review.pk].ok)
        self.assertIn("Approved", by_id[still_in_review.pk].message)

        approved.refresh_from_db()
        still_in_review.refresh_from_db()
        self.assertEqual(approved.status, Article.Status.SCHEDULED)
        self.assertEqual(still_in_review.status, Article.Status.IN_REVIEW)

    def test_bulk_unpublish_mixed_results(self):
        approved = self._article(Article.Status.APPROVED)
        services.publish(approved, actor=self.editor)
        draft = self._article(Article.Status.DRAFT)

        results = services.bulk_unpublish([approved.pk, draft.pk], actor=self.editor)
        by_id = {r.article.pk: r for r in results}
        self.assertTrue(by_id[approved.pk].ok)
        self.assertFalse(by_id[draft.pk].ok)


class OverdueAlertTests(TestCase):
    def setUp(self):
        self.editor = make_user("editor@example.com", User.Role.EDITOR)
        self.writer = make_user("writer@example.com", User.Role.WRITER)
        self.section = Section.objects.create(name="Politics", owning_editor=self.editor)
        SectionAssignment.objects.create(section=self.section, user=self.writer)
        self.article = services.create_article(
            title="A", body="B", section=self.section, author=self.writer
        )
        services.submit_for_review(self.article, actor=self.writer)
        services.approve(self.article, actor=self.editor)

    def _make_overdue(self):
        services.schedule(self.article, actor=self.editor, publish_at=timezone.now() + timedelta(hours=1))
        Article.objects.filter(pk=self.article.pk).update(publish_at=timezone.now() - timedelta(hours=1))
        self.article.refresh_from_db()

    def test_scheduled_in_future_is_not_overdue(self):
        services.schedule(self.article, actor=self.editor, publish_at=timezone.now() + timedelta(days=1))
        self.assertEqual(services.overdue_articles(), [])

    def test_scheduled_in_past_is_overdue(self):
        self._make_overdue()
        overdue = services.overdue_articles()
        self.assertEqual([a.pk for a in overdue], [self.article.pk])

    def test_dismiss_clears_the_alert(self):
        self._make_overdue()
        services.dismiss_alert(self.article, actor=self.editor)
        self.assertEqual(services.overdue_articles(), [])

    def test_dismissal_does_not_survive_a_reschedule(self):
        self._make_overdue()
        services.dismiss_alert(self.article, actor=self.editor)

        # Re-publish then unpublish to get back to Approved, then reschedule
        # and let the new publish_at go overdue too.
        services.publish(self.article, actor=self.editor)
        services.unpublish(self.article, actor=self.editor)
        self._make_overdue()

        overdue = services.overdue_articles()
        self.assertEqual([a.pk for a in overdue], [self.article.pk])
        self.assertEqual(ArticleAlertDismissal.objects.count(), 1)

    def test_only_editor_can_dismiss(self):
        self._make_overdue()
        with self.assertRaises(services.TransitionError):
            services.dismiss_alert(self.article, actor=self.writer)


class SearchAndPermissionViewTests(TestCase):
    def setUp(self):
        self.editor = make_user("editor@example.com", User.Role.EDITOR)
        self.writer = make_user("writer@example.com", User.Role.WRITER)
        self.outsider = make_user("outsider@example.com", User.Role.WRITER)
        self.section = Section.objects.create(name="Politics", owning_editor=self.editor)
        SectionAssignment.objects.create(section=self.section, user=self.writer)
        self.article = services.create_article(
            title="Budget vote passes", body="Council details inside.",
            section=self.section, author=self.writer,
        )

    def test_search_matches_title_and_body(self):
        self.assertIn(self.article, services.search_articles(self.editor, q="budget"))
        self.assertIn(self.article, services.search_articles(self.editor, q="council"))
        self.assertNotIn(self.article, services.search_articles(self.editor, q="nonexistent"))

    def test_outsider_writer_does_not_see_article(self):
        self.assertNotIn(self.article, services.visible_articles(self.outsider))

    def test_outsider_gets_404_on_detail_view(self):
        self.client.force_login(self.outsider)
        response = self.client.get(reverse("articles:detail", args=[self.article.pk]))
        self.assertEqual(response.status_code, 404)

    def test_bulk_action_endpoint_is_editor_only(self):
        self.client.force_login(self.writer)
        response = self.client.post(reverse("articles:bulk_action"), {"action": "unpublish", "article_ids": str(self.article.pk)})
        self.assertEqual(response.status_code, 403)

    def test_approve_endpoint_rejects_non_editor_via_service_layer(self):
        services.submit_for_review(self.article, actor=self.writer)
        self.client.force_login(self.writer)
        response = self.client.post(reverse("articles:approve", args=[self.article.pk]), follow=True)
        self.article.refresh_from_db()
        self.assertEqual(self.article.status, Article.Status.IN_REVIEW)
        messages = [str(m) for m in response.context["messages"]]
        self.assertTrue(any("editor" in m.lower() for m in messages))
