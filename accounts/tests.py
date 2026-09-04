from django.db import IntegrityError, transaction
from django.test import TestCase

from accounts.models import User


class UserRoleTests(TestCase):
    def test_default_role_is_writer(self):
        user = User.objects.create_user(username="a", email="a@example.com", password="x")
        self.assertEqual(user.role, User.Role.WRITER)
        self.assertTrue(user.is_writer)
        self.assertFalse(user.is_editor)

    def test_editor_role_flags(self):
        user = User.objects.create_user(
            username="e", email="e@example.com", password="x", role=User.Role.EDITOR
        )
        self.assertTrue(user.is_editor)
        self.assertFalse(user.is_writer)

    def test_login_uses_email(self):
        User.objects.create_user(username="a", email="a@example.com", password="secret-pass")
        self.assertTrue(self.client.login(username="a@example.com", password="secret-pass"))

    def test_email_must_be_unique(self):
        User.objects.create_user(username="a", email="dupe@example.com", password="x")
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                User.objects.create_user(username="b", email="dupe@example.com", password="x")
