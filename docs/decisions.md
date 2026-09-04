# Decisions

## Decision 1

- **Chose:** A single server-rendered Django app (views + templates, Bootstrap via CDN) as the
  whole submission.
- **Rejected:** A Django REST Framework API behind a separate React/Vue frontend, deployed as two
  services (matching the README's Render + Vercel example literally).
- **Why:** The actual hard part of this brief is the workflow logic (goal #4's transition rules,
  goal #7's per-article bulk reporting, goal #10's dismiss/reappear alert semantics) — none of
  that gets easier with a JSON API in front of it, and a split frontend adds a serializer layer,
  an API client, CORS/auth-token handling, and a second build/deploy pipeline, none of which
  moves any of the ten goals forward. Given the ~12 hour budget, that overhead is exactly the
  kind of "impress with tooling" spend the brief explicitly says not to make.

## Decision 2

- **Chose:** SQLite for local development and the test suite; Postgres (Supabase) only in
  production, switched purely via the `DATABASE_URL` env var that `django-environ` already reads.
- **Rejected:** Requiring a local Postgres instance (or Docker) for every environment, so dev
  exactly matches prod.
- **Why:** Nothing in this schema uses a Postgres-only feature (no `ArrayField`, no native
  full-text search, no `JSONField` querying) — every constraint in `schema.md` is portable SQL.
  Removing "have Postgres running" as a precondition for `python manage.py test` matters more
  for iteration speed than environment parity does here, and the swap is one env var, not a
  settings fork.

## Decision 3

- **Chose:** Comments are `ArticleEvent` rows (`event_type="comment"`, text in `note`) — no
  separate `Comment` model.
- **Rejected:** A dedicated `Comment` model, FK'd to `Article`, separate from the event log.
- **Why:** Goal #9 already requires one append-only, unified timeline of "created, every status
  change, every revision, and any comments." Building a second table and then merging two
  queries (events + comments, sorted together) to render that one timeline would be more code
  producing the exact same view. If a stretch goal like passage-level comment threads gets built
  later, *that* needs its own model (it has real extra fields — an anchor position, a thread
  parent) — but a flat comment doesn't.

## Decision 4

- **Chose:** Moving a `Scheduled` article to `Published` is a manual editor action (the same
  "Publish now" button works from both `Approved` and `Scheduled`), not an automatic transition
  that fires when `publish_at` arrives.
- **Rejected:** A Celery beat / cron job that flips `Scheduled` → `Published` the moment the
  clock passes `publish_at`.
- **Why:** The brief's goal #10 only makes sense under this reading. If the system auto-published
  on time, a `Scheduled` article could never actually *be* overdue — it'd already be `Published`
  the instant it was late. Goal #10 describes overdue as a real, persistent state editors have to
  notice and act on ("An editor can dismiss the alert"), which only exists if publishing is
  something a person does. It also means there's no scheduler process to run, deploy, or keep
  alive on a free host — see `architecture.md`.

## Decision 5

- **Chose:** When a revision reaches `Published`, its content is copied onto the parent article
  (whose own content the reader sees), but the revision row itself stays in the database, visible
  in search results and the calendar export, exactly like any other `Published` article.
- **Rejected:** Deleting the revision row after merging, or hiding it from article lists once
  applied.
- **Why:** Goal #9 requires the timeline to show "every revision opened and whether it was
  published" — that's not knowable after the fact if the published revision no longer exists.
  The trade-off is that a merged revision and its parent can briefly show the same title in a
  list (both `Published`, same content) — I judged staying honest to the append-only history
  requirement as the more important of the two.

## Decision 6

- **Chose:** The bulk-select checkboxes on the article list use no `name` attribute at all;
  a small JS handler collects the checked values on submit and writes them into one hidden
  `article_ids` field as a comma-joined string, which is what `BulkActionForm` actually parses.
- **Rejected (my first pass):** Giving each checkbox `name="article_ids"` directly, relying on
  the browser to submit one `article_ids` value per checked box.
- **Why — and why I reversed it:** The first version looked reasonable — multiple same-named
  checkboxes is the standard HTML pattern for a multi-select — but `BulkActionForm.article_ids`
  is a `CharField`, and Django's `QueryDict.get()` for a repeated key returns only the *last*
  value, not the list. Manually testing the bulk-schedule flow against the running server (one
  editor session scheduling a real selection of articles) surfaced this immediately: only the
  last-checked article ever made it into the request. I switched the checkboxes to unnamed
  (JS-only) and kept `article_ids` as a single hidden field the JS builds explicitly, which is
  what the form was actually written to parse. Running the server and clicking through a flow by
  hand — not just unit tests against the service layer — is what caught this; it's now in
  `docs/plan.md` as a reason I kept doing that for every user-facing feature, not just the
  lifecycle logic.
