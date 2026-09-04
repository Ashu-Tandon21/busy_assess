from django.test import TestCase
from django.urls import reverse

from accounts.models import User
from articles import services as article_services

from .models import Section, SectionAssignment
from .services import assignable_sections, visible_sections


def make_user(email, role):
    return User.objects.create_user(username=email.split("@")[0], email=email, password="pw12345", role=role)


class SectionVisibilityTests(TestCase):
    def setUp(self):
        self.editor = make_user("editor@example.com", User.Role.EDITOR)
        self.writer = make_user("writer@example.com", User.Role.WRITER)
        self.other_writer = make_user("other@example.com", User.Role.WRITER)
        self.assigned = Section.objects.create(name="Politics", owning_editor=self.editor)
        self.unassigned = Section.objects.create(name="Culture", owning_editor=self.editor)
        self.archived = Section.objects.create(
            name="Old desk", owning_editor=self.editor, is_archived=True
        )
        SectionAssignment.objects.create(section=self.assigned, user=self.writer)

    def test_editor_sees_all_non_archived_by_default(self):
        pks = set(visible_sections(self.editor).values_list("pk", flat=True))
        self.assertEqual(pks, {self.assigned.pk, self.unassigned.pk})

    def test_editor_can_include_archived(self):
        pks = set(visible_sections(self.editor, include_archived=True).values_list("pk", flat=True))
        self.assertIn(self.archived.pk, pks)

    def test_writer_sees_only_assigned_sections(self):
        pks = set(visible_sections(self.writer).values_list("pk", flat=True))
        self.assertEqual(pks, {self.assigned.pk})

    def test_unassigned_writer_sees_nothing(self):
        pks = set(visible_sections(self.other_writer).values_list("pk", flat=True))
        self.assertEqual(pks, set())

    def test_archiving_does_not_delete_articles(self):
        article = article_services.create_article(
            title="Piece", body="Body", section=self.assigned, author=self.writer
        )
        self.assigned.is_archived = True
        self.assigned.save()
        article.refresh_from_db()
        self.assertEqual(article.section_id, self.assigned.pk)
        self.assertNotIn(self.assigned.pk, visible_sections(self.editor).values_list("pk", flat=True))

    def test_writer_cannot_create_in_unassigned_section(self):
        self.assertNotIn(self.unassigned, assignable_sections(self.writer))


class SectionPermissionViewTests(TestCase):
    def setUp(self):
        self.editor = make_user("editor@example.com", User.Role.EDITOR)
        self.writer = make_user("writer@example.com", User.Role.WRITER)
        self.section = Section.objects.create(name="Politics", owning_editor=self.editor)

    def test_writer_cannot_create_section(self):
        self.client.force_login(self.writer)
        response = self.client.get(reverse("sections:create"))
        self.assertEqual(response.status_code, 403)

    def test_writer_cannot_archive_section(self):
        self.client.force_login(self.writer)
        response = self.client.post(reverse("sections:archive_toggle", args=[self.section.pk]))
        self.assertEqual(response.status_code, 403)

    def test_writer_cannot_assign_writers(self):
        other = make_user("w2@example.com", User.Role.WRITER)
        self.client.force_login(self.writer)
        response = self.client.post(
            reverse("sections:assign_writer", args=[self.section.pk]), {"writer": other.pk}
        )
        self.assertEqual(response.status_code, 403)

    def test_editor_can_assign_and_remove_writer(self):
        self.client.force_login(self.editor)
        self.client.post(reverse("sections:assign_writer", args=[self.section.pk]), {"writer": self.writer.pk})
        self.assertTrue(SectionAssignment.objects.filter(section=self.section, user=self.writer).exists())

        self.client.post(reverse("sections:remove_writer", args=[self.section.pk, self.writer.pk]))
        self.assertFalse(SectionAssignment.objects.filter(section=self.section, user=self.writer).exists())
