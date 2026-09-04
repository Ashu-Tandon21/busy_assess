# Architecture

## What are the moving pieces, and how do they talk to each other?

One Django project, three apps:

- **`accounts`** — a custom `User` model (email as the login identifier, a `role` field of
  `editor`/`writer`) plus `EditorRequiredMixin`, the one place the "is this user an editor"
  check lives for view-level gating.
- **`sections`** — `Section` and the `SectionAssignment` join table (who's assigned where).
  `sections/services.py` holds the visibility rules (`visible_sections`, `assignable_sections`)
  that both the sections app and the articles app import — a writer's "which sections can I see
  / write into" answer needs to be the same everywhere it's asked.
- **`articles`** — `Article`, the append-only `ArticleEvent` (timeline entries: created,
  status changes, revisions opened, comments), and `ArticleAlertDismissal`. All the actual
  business logic — every lifecycle transition, search, bulk actions, dashboard aggregates,
  overdue-alert lookup — lives in `articles/services.py` as one function per operation. Views
  are thin: parse the request, call a service function, catch `TransitionError`, show its
  message.

There's no separate API layer and no JS frontend framework — views render Django templates
server-side (Bootstrap via CDN for styling, a little vanilla JS for the bulk-select checkboxes
and the dashboard's Chart.js chart). See `decisions.md` for why.

## Where does each piece run?

Everything above runs in one process: Django (via Gunicorn in production, `runserver` locally)
handling both the page rendering and the data access. It talks to one external piece — Postgres
(Supabase in production, SQLite locally) — over a normal DB connection using `DATABASE_URL`.
Static assets (CSS/JS from Bootstrap's CDN, plus Django's own admin/static files) are served by
WhiteNoise from inside the same process rather than a separate static host, since there's little
enough of it that a CDN/S3 split wasn't worth the extra moving part.

## Request path: an editor approves an article

1. Browser: `POST /articles/42/approve/`, with the CSRF token from the article detail page's
   form and the session cookie.
2. Django's `AuthenticationMiddleware` attaches `request.user` from the session.
3. `ApproveView.post()` (`articles/views.py`) loads the article via
   `_get_visible_article_or_404`, which restricts the lookup to
   `services.visible_articles(request.user)` — an editor sees everything, so this doesn't
   narrow anything for an editor, but the same code path is shared with writer-triggered actions
   (like `submit`), where it does.
4. The view calls `services.approve(article, actor=request.user)`. That function is the actual
   authority: it checks `actor.is_editor`, checks `article.status == IN_REVIEW`, checks
   `article.author_id != actor.id` — the three rules the brief spells out for this move — and
   raises `TransitionError` with a specific message if any of them fail. This check runs
   regardless of what the UI showed or hid, which is what "enforced on the server" in goal #1
   means in practice.
5. On success, the function flips `article.status` to `APPROVED`, saves, and writes an
   `ArticleEvent(event_type=STATUS_CHANGE, old_status=IN_REVIEW, new_status=APPROVED, actor=...)`
   inside the same DB transaction (`@transaction.atomic`) — the status change and its history
   entry either both happen or neither does.
6. The view catches nothing (success path), sets a success flash message, and redirects back to
   the article detail page (`302` → `GET /articles/42/`), which re-renders showing the new
   status and the new timeline entry.

An illegal call (say, the article's own author trying this) takes the same path through step 4,
but `services.approve` raises `TransitionError("You cannot approve your own article.")`; the view
catches it, turns it into an error flash message, and redirects back without touching the
database. Nothing about steps 1–3 changes — the rejection happens in exactly one place.

## What did you decide *not* to build, and why?

- **No separate frontend/API split.** A JSON API plus a React (or similar) frontend would double
  the surface area — auth handling, serializers, an API client, a build pipeline, two deploys —
  for an app whose actual complexity is in the workflow rules, not the UI. Server-rendered
  templates get all ten goals built and tested inside the time budget; see `decisions.md`.
- **No background job runner / scheduler.** A Scheduled article does *not* auto-flip to
  Published when its time arrives — that's deliberate (see `decisions.md`, "manual publish over
  a scheduler"), and it means there's no Celery/cron/queue to run, deploy, and keep alive on a
  free tier.
- **No separate `Comment` model.** Comments are just another `ArticleEvent` row
  (`event_type=comment`, `note=<text>`). A dedicated model would let a comment carry its own
  fields (e.g. a reply-to link) later, but nothing in the brief asks for that, and one append-only
  table serving as the whole timeline is simpler to reason about and query.
- **No user self-signup.** The brief describes a small, roster-based newsroom — editors assign
  writers to sections, not the other way around — so account creation is a superuser/admin/seed
  concern, not a public flow. `python manage.py seed_demo` and Django admin cover it.
- **No object-level permissions library (e.g. django-guardian).** Every permission check in this
  app reduces to "editor, or the article's own author" — a couple of `if` statements in
  `services.py`, not a rule engine. Pulling in a permissions framework for two rules would be
  more code to explain, not less.
