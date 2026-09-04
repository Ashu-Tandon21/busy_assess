"""Seeds enough demo data to show every goal in the brief actually working.

Deliberately drives everything through articles.services (not raw model
writes) so the seeded articles carry a real, believable history — the same
functions the UI calls. The one exception is backdating a couple of
publish_at values to demonstrate the overdue-alert goal, which the service
layer correctly refuses to do for a *new* schedule() call.
"""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from accounts.models import User
from articles import services
from articles.models import Article
from sections.models import Section, SectionAssignment

DEMO_PASSWORD = "DemoPass123!"


class Command(BaseCommand):
    help = "Seed demo editors, writers, sections and articles across every lifecycle state."

    def add_arguments(self, parser):
        parser.add_argument(
            "--reset",
            action="store_true",
            help="Delete existing sections/articles/users (except a real superuser) before seeding.",
        )

    def handle(self, *args, **options):
        if options["reset"]:
            self._reset()

        if Article.objects.exists():
            self.stdout.write(self.style.WARNING("Data already present — skipping. Use --reset to reseed."))
            return

        with transaction.atomic():
            editors = self._make_users(
                [
                    ("nadia.editor@example.com", "nadia.editor"),
                    ("sam.editor@example.com", "sam.editor"),
                ],
                User.Role.EDITOR,
            )
            writers = self._make_users(
                [
                    ("amy.writer@example.com", "amy.writer"),
                    ("ben.writer@example.com", "ben.writer"),
                    ("cleo.writer@example.com", "cleo.writer"),
                    ("dev.writer@example.com", "dev.writer"),
                ],
                User.Role.WRITER,
            )
            nadia, sam = editors
            amy, ben, cleo, dev = writers

            politics = Section.objects.create(
                name="Politics", description="National and local politics.", owning_editor=nadia
            )
            culture = Section.objects.create(
                name="Culture", description="Arts, books, and the rest of it.", owning_editor=nadia
            )
            tech = Section.objects.create(
                name="Tech", description="Products, platforms, and the industry around them.",
                owning_editor=sam,
            )
            obituaries = Section.objects.create(
                name="Obituaries", description="Retired section — no longer staffed.",
                owning_editor=sam, is_archived=True,
            )

            for section, assigned in [
                (politics, [amy, ben]),
                (culture, [cleo, amy]),
                (tech, [dev, ben]),
                (obituaries, [dev]),
            ]:
                for writer in assigned:
                    SectionAssignment.objects.get_or_create(section=section, user=writer)

            self._seed_articles(politics, culture, tech, editors=(nadia, sam), writers=(amy, ben, cleo, dev))

        self.stdout.write(self.style.SUCCESS("Seeded demo data."))
        self.stdout.write(f"Demo password for every account: {DEMO_PASSWORD}")
        for user in User.objects.order_by("role", "email"):
            self.stdout.write(f"  {user.email} ({user.role})")

    def _reset(self):
        Article.objects.all().delete()
        Section.objects.all().delete()
        User.objects.filter(is_superuser=False).delete()
        self.stdout.write(self.style.WARNING("Cleared existing sections, articles, and non-superuser users."))

    def _make_users(self, pairs, role):
        made = []
        for email, username in pairs:
            user, created = User.objects.get_or_create(
                email=email, defaults={"username": username, "role": role}
            )
            if created:
                user.set_password(DEMO_PASSWORD)
                user.save()
            made.append(user)
        return made

    def _seed_articles(self, politics, culture, tech, *, editors, writers):
        nadia, sam = editors
        amy, ben, cleo, dev = writers
        now = timezone.now()

        # 1. Plain draft, untouched.
        services.create_article(
            title="Council votes on transit budget",
            body="A draft still being worked on.",
            section=politics, author=amy,
        )

        # 2. In review, waiting on an editor.
        a2 = services.create_article(
            title="City council preview: what's on the agenda",
            body="Full body of the preview article goes here.",
            section=politics, author=ben,
        )
        services.submit_for_review(a2, actor=ben)

        # 3. Approved (editor other than the author approved it).
        a3 = services.create_article(
            title="Gallery reopens after two-year renovation",
            body="The gallery on Fifth reopens Thursday with a members' preview.",
            section=culture, author=cleo,
        )
        services.submit_for_review(a3, actor=cleo)
        services.approve(a3, actor=nadia)

        # 4. Scheduled for later this week.
        a4 = services.create_article(
            title="Streaming platform changes its recommendation algorithm",
            body="A look at what changed and what it means for smaller publishers.",
            section=tech, author=dev,
        )
        services.submit_for_review(a4, actor=dev)
        services.approve(a4, actor=sam)
        services.schedule(a4, actor=sam, publish_at=now + timedelta(days=2))

        # 5. Overdue: was scheduled, publish time has already passed.
        a5 = services.create_article(
            title="Chipmaker delays next-gen launch",
            body="The delay pushes the launch into next quarter.",
            section=tech, author=ben,
        )
        services.submit_for_review(a5, actor=ben)
        services.approve(a5, actor=sam)
        services.schedule(a5, actor=sam, publish_at=now + timedelta(hours=1))
        Article.objects.filter(pk=a5.pk).update(publish_at=now - timedelta(hours=5))

        # 6. Published, straightforward.
        a6 = services.create_article(
            title="What the new city budget actually funds",
            body="A breakdown of where the money goes this year.",
            section=politics, author=amy,
        )
        services.submit_for_review(a6, actor=amy)
        services.approve(a6, actor=nadia)
        services.publish(a6, actor=nadia)
        services.add_comment(a6, actor=nadia, text="Good clarity on the numbers — nice work.")

        # 7. Published, then a follow-up revision was opened (still Draft).
        a7 = services.create_article(
            title="Author interview: on writing through a decade of change",
            body="An extended interview about craft and process.",
            section=culture, author=cleo,
        )
        services.submit_for_review(a7, actor=cleo)
        services.approve(a7, actor=nadia)
        services.publish(a7, actor=nadia)
        services.open_revision(a7, actor=cleo)

        # 8. Published, then corrected via a revision that has itself gone live —
        #    demonstrates the content-replacement rule.
        a8 = services.create_article(
            title="Startup raises new funding round",
            body="Original figures as first reported.",
            section=tech, author=dev,
        )
        services.submit_for_review(a8, actor=dev)
        services.approve(a8, actor=sam)
        services.publish(a8, actor=sam)
        revision = services.open_revision(a8, actor=dev)
        revision.title = "Startup raises new funding round (corrected)"
        revision.body = "Corrected figures after the company clarified the round size."
        revision.save(update_fields=["title", "body"])
        services.submit_for_review(revision, actor=dev)
        services.approve(revision, actor=sam)
        services.publish(revision, actor=sam)

        # 9. Unpublished back to Approved for a wording fix.
        a9 = services.create_article(
            title="Weekend arts roundup",
            body="Five things worth seeing this weekend.",
            section=culture, author=amy,
        )
        services.submit_for_review(a9, actor=amy)
        services.approve(a9, actor=nadia)
        services.publish(a9, actor=nadia)
        services.unpublish(a9, actor=nadia)
