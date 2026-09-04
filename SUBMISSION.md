# Submission

Fill this in and commit it. This is the first file we open.

## Links

- **GitHub repository:** <public repo URL — push this repo and paste it here>
- **Live application:** <not yet deployed — see "Notes for the reviewer">

## Notes for the reviewer

This repository is built and passing its own test suite (`python manage.py test`, 50 tests) but
has **not been deployed yet** — `build.sh`, `Procfile`, and `render.yaml` are written and
`config/settings.py` is production-ready (see the `DEBUG=False` branch: HTTPS redirect, secure
cookies, WhiteNoise static serving), but no Supabase project or Render service has actually been
created. `docs/plan.md` explains why honestly. Before submitting for real:

1. Create a Supabase (or any managed Postgres) project; copy its connection string.
2. Deploy this repo to Render (or any host) as a single web service, `./build.sh` as the build
   command, `gunicorn config.wsgi --log-file -` as the start command.
3. Set env vars: `SECRET_KEY` (generate one), `DEBUG=False`, `ALLOWED_HOSTS` and
   `CSRF_TRUSTED_ORIGINS` to the deployed hostname, `DATABASE_URL` to the Supabase string.
4. Once live, run `python manage.py seed_demo` against it (via a Render shell or a one-off job)
   so the deployed instance has real demo data, then fill in the two links above and the demo
   credentials below with real values, and remove this notice.

Free tiers (Render's included) sleep when idle — note that in this section once deployed, so a
slow first load isn't read as broken.

## Demo credentials

Seeded by `python manage.py seed_demo` (see `articles/management/commands/seed_demo.py`). The
same password is set for every seeded account:

| Role | Email | Password |
|------|-------|----------|
| Editor | nadia.editor@example.com | DemoPass123! |
| Editor | sam.editor@example.com | DemoPass123! |
| Writer | amy.writer@example.com | DemoPass123! |
| Writer | ben.writer@example.com | DemoPass123! |
| Writer | cleo.writer@example.com | DemoPass123! |
| Writer | dev.writer@example.com | DemoPass123! |

A Django superuser (for `/admin/`) is created separately with `python manage.py createsuperuser`
— not part of the seed command, and not listed here since its credentials are host-specific.

## Stack

| Layer | What you used | Why |
|-------|---------------|-----|
| Frontend | Django templates + Bootstrap 5 (CDN) + a little vanilla JS; Chart.js (CDN) for the dashboard chart | Server-rendered — no separate frontend build/deploy. See `docs/decisions.md` #1. |
| Backend | Django 5.2 | Batteries-included auth, ORM, admin, and forms cover everything this app needs without extra libraries. |
| Database | PostgreSQL (Supabase) in production; SQLite locally and for tests | See `docs/decisions.md` #2. |
| Hosting | Render (web service) + Supabase (database) — see `render.yaml` / `build.sh` | Matches the README's suggested free-tier combo; not yet actually deployed (see above). |

## Goal checklist

| # | Goal | Status | Notes |
|---|------|--------|-------|
| 1 | Accounts and roles | Done | Custom `User` (email login, `editor`/`writer` role). Every state-changing view goes through `articles/services.py` / `sections/services.py`, which re-check role and authorship server-side regardless of what the UI shows — see `accounts/mixins.py` and the service functions. |
| 2 | Sections | Done | Create/edit (editor-only), archive/restore. Archiving hides from the default section list but articles and data are untouched — covered by `sections/tests.py::test_archiving_does_not_delete_articles`. |
| 3 | Articles inside sections | Done | One section per article, title/body/author, writer-creates/edits-own, editor-edits-any. |
| 4 | Article lifecycle with rules | Done | Every transition in `articles/services.py`, one function each, with the exact illegal-move messages the brief calls for. 20+ tests in `articles/tests.py::ArticleLifecycleTests`. See `docs/decisions.md` #4 and #5 for the two genuinely ambiguous rules (Scheduled→Published, and what happens to a revision after it merges). |
| 5 | Section assignments | Done | Editor-only assign/remove (`sections/views.py`), "my sections" and "my articles" both just filtered queryset views using the same `sections/services.py::visible_sections`. |
| 6 | Finding articles | Done | `articles/views.py::article_list` — server-side search (title+body), filters (section/status/author), sort (updated/status/publish time), and `Paginator`-based pagination with a total count. Nothing is loaded into the browser to filter client-side. |
| 7 | Acting on many articles at once | Done | Bulk schedule/unpublish with a per-article success/failure report (`articles/services.py::bulk_schedule`/`bulk_unpublish`, rendered by `templates/articles/bulk_result.html`); CSV calendar export at `/articles/export/calendar.csv`. |
| 8 | Dashboard | Done | Headline counts, by-status and by-section breakdowns, and an 8-week published-per-week Chart.js chart — all from `articles/services.py::dashboard_stats`. |
| 9 | History you cannot rewrite | Done | `ArticleEvent` is append-only at the model level (`save()`/`delete()` raise after creation; a custom manager's `QuerySet.update()`/`.delete()` also raise) — covered by `articles/tests.py::test_comment_is_recorded_and_append_only`. |
| 10 | Overdue publish alerts | Done | `articles/services.py::overdue_articles` + `dismiss_alert`; a nav badge context processor (`articles/context_processors.py`) shows the count on every page. Dismissal is keyed on `(article, publish_at)`, so a reschedule that goes overdue again re-alerts — tested directly in `OverdueAlertTests`. |

Every row above is backed by tests — `python manage.py test` (50 tests) is green as of the last
commit in this repo.

## How much time did you actually spend?

Not paced against the suggested 12-hours-over-a-week; see `docs/plan.md` for the honest version
of how this was actually built.

## What would you do next, with another 12 hours?

- Actually deploy it (Supabase + Render), verify the live URL, and fill in the links above.
- Full-text or trigram search index for the title/body search — see `docs/schema.md`'s "what
  breaks first at 100x" section; the current `icontains` query is the first thing that wouldn't
  scale.
- A visual diff between a revision and its parent (one of the brief's stretch ideas) — the data
  to build it already exists (`Article.revision_of`), just no UI for it yet.
- Load-test the "100x the data" claims in `docs/schema.md` against an actually-seeded 100x
  dataset instead of reasoning from the query shapes alone.

## What are you least happy with in this codebase, and why?

The article list template (`templates/articles/list.html`) mixes the bulk-action `<form>` around
the results table with the filter `<form>` above it using plain HTML/vanilla JS rather than a
small dedicated component — it works (see `docs/decisions.md` #6 for the one real bug that
surfaced here and got fixed), but it's the one place in this codebase where "just enough JS to
make it work" shows, rather than a clean pattern I'd want to defend as *the* way to do it if this
app grew a third or fourth similar bulk-selection feature.
