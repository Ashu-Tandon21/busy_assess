"""Shared server-side role gates.

These mixins are the enforcement point — templates may also hide buttons a
user can't use, but that's cosmetic. Every view that changes state re-checks
the role here (or, for article lifecycle moves, inside articles.services),
so a crafted request from the browser can't skip the check the UI happens to
hide.
"""

from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin


class EditorRequiredMixin(LoginRequiredMixin, UserPassesTestMixin):
    """Restricts a view to authenticated users with the editor role."""

    def test_func(self) -> bool:
        return self.request.user.is_editor
