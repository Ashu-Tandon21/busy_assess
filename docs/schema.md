# Schema

## Tables

### `accounts_user` (custom `User`, extends Django's `AbstractUser`)

| Column | Type | Notes |
|---|---|---|
| id | bigint, PK | |
| username | varchar(150), unique | kept because `AbstractUser` requires it; not used to log in |
| email | varchar(254), unique | `USERNAME_FIELD` — this is what people actually log in with |
| password | varchar(128) | Django's salted-hash format |
| role | varchar(20) | `editor` \| `writer` |
| first_name, last_name | varchar(150) | unused by the app, kept from `AbstractUser` |
| is_staff, is_superuser, is_active | boolean | Django admin/auth plumbing |
| last_login, date_joined | timestamptz | |

Plus the two standard `AbstractUser` many-to-many tables (`groups`, `user_permissions`) — present
because `AbstractUser` brings them, unused by this app's own permission logic.

### `sections_section`

| Column | Type | Notes |
|---|---|---|
| id | bigint, PK | |
| name | varchar(150) | |
| description | text | blank allowed |
| owning_editor_id | FK → `accounts_user`, `PROTECT` | must have `role='editor'` (enforced by `limit_choices_to` in the form/admin, **not** a DB constraint — see below) |
| is_archived | boolean, default false | |
| created_at | timestamptz | |

### `sections_sectionassignment` (the Section ↔ writer join table)

| Column | Type | Notes |
|---|---|---|
| id | bigint, PK | |
| section_id | FK → `sections_section`, `CASCADE` | |
| user_id | FK → `accounts_user`, `CASCADE` | must have `role='writer'` (same caveat as above) |
| created_at | timestamptz | |
| — | `UNIQUE(section_id, user_id)` | a writer can't be assigned to the same section twice |

### `articles_article`

| Column | Type | Notes |
|---|---|---|
| id | bigint, PK | |
| title | varchar(255) | |
| body | text | |
| author_id | FK → `accounts_user`, `PROTECT` | |
| section_id | FK → `sections_section`, `PROTECT` | |
| status | varchar(20), indexed | `draft`\|`in_review`\|`approved`\|`scheduled`\|`published` |
| publish_at | timestamptz, nullable, indexed | set on schedule/publish; cleared when edited back to review |
| created_at, updated_at | timestamptz | |
| revision_of_id | FK → `articles_article` (self), `PROTECT`, nullable | non-null only on a revision row |
| — | `CHECK(id <> revision_of_id)` | can't be your own revision |

### `articles_articleevent` (the append-only timeline)

| Column | Type | Notes |
|---|---|---|
| id | bigint, PK | |
| article_id | FK → `articles_article`, `PROTECT` | |
| event_type | varchar(32), indexed | `created`\|`status_change`\|`revision_opened`\|`comment` |
| old_status, new_status | varchar(20), nullable | populated for `status_change` events |
| actor_id | FK → `accounts_user`, `PROTECT` | who did it |
| note | text, nullable | free text — a comment's body, *or* a system note (e.g. "Revision #7 opened") |
| created_at | timestamptz, indexed | |

### `articles_articlealertdismissal`

| Column | Type | Notes |
|---|---|---|
| id | bigint, PK | |
| article_id | FK → `articles_article`, `PROTECT` | |
| publish_at | timestamptz | the specific overdue `publish_at` being dismissed |
| dismissed_by_id | FK → `accounts_user`, `PROTECT` | must be an editor (form-level, not DB) |
| dismissed_at | timestamptz | |
| — | `UNIQUE(article_id, publish_at)` | this is the whole mechanism — see below |

## Relationships

One-to-many:
- `User` (editor) → `Section` (`owning_editor`)
- `User` (author) → `Article`
- `Section` → `Article`
- `Article` → `Article` (`revision_of`, self-referential)
- `Article` → `ArticleEvent`
- `Article` → `ArticleAlertDismissal`

Many-to-many:
- `Section` ↔ `User` (writers), through `SectionAssignment` — the only genuine M2M in the schema;
  everything else is a plain FK.

## Constraints: database vs. application

**In the database:** every FK's referential integrity (and its `PROTECT`/`CASCADE` behaviour —
you can't delete an editor who still owns sections, or an author who still has articles, but
removing a writer from a section cascades the one join row); `NOT NULL` on required columns;
`UNIQUE` on email/username, on `(section, user)`, and on `(article, publish_at)`; the
self-reference `CHECK` on `revision_of`.

**In application code, deliberately:**
- **Role restrictions on a FK's target** (`owning_editor` must be an editor, `SectionAssignment.user`
  must be a writer) are `limit_choices_to` — a UI/admin hint, not a DB `CHECK`. A `CHECK` can't
  reference another table's column in Postgres without a trigger, and a trigger for something a
  service-layer function already guarantees on every write path felt like the wrong place to put
  it. If this schema ever gets a second write path outside Django (a script, another service), this
  is the one that should move to the database.
- **Every lifecycle rule** — legal status transitions, "author can't approve their own article",
  "only an assigned writer can create in a section", "editing an Approved/Scheduled article sends
  it back to review" — lives entirely in `articles/services.py` and `sections/services.py`. None
  of it is expressible as a column constraint (it depends on *who* is asking, not just the row's
  own values), so there was never a real choice here.
- **Append-only `ArticleEvent`** is enforced by overriding `save()`/`delete()` on the model and by
  a custom manager whose `QuerySet.update()`/`.delete()` raise. This is an application-level
  promise, not a database one — a `REVOKE UPDATE, DELETE` on the table role would be the DB-level
  version, and would be the right hardening step before this app got a second, less-trusted write
  path (see `architecture.md`'s scope decisions).

## What was deliberately denormalised

- `ArticleEvent.old_status`/`new_status` duplicate information that's technically derivable by
  looking at the previous event for the same article — but re-deriving "what was the status right
  before this change" on every timeline render would mean an extra self-join or window function
  per row. Storing both ends of every transition costs two small varchar columns and makes the
  timeline a single indexed `SELECT ... WHERE article_id = ? ORDER BY created_at` with no
  further computation.
- `ArticleEvent.note` is one column serving two purposes (a human comment's text, and a
  system-generated note like "Revision #7 opened"). Splitting these into `comment_text` and
  `system_note` would make the two `event_type`s that use it slightly more self-documenting, but
  every current reader (the timeline template) already branches on `event_type` first, so the
  split wouldn't remove any code — see `decisions.md`.

## What would break first at 100x the data

Two things, in this order:

1. **Free-text search on `title`/`body`** (`icontains` on both, `OR`ed together). Postgres will
   happily run this as a sequential scan today; at 100x the row count it's a full-text scan on
   every search request with no index to use — this is the first thing a real newsroom's article
   count would make painfully slow. The fix is a Postgres full-text (`tsvector`/GIN) or trigram
   (`pg_trgm`) index on `title`/`body`, which changes the query but not the schema's shape.
2. **`services.overdue_articles()`** pulls every overdue `Scheduled` article and every relevant
   `ArticleAlertDismissal` into Python and does the (article, publish_at) exclusion as a set
   difference in application code, rather than as a single `NOT EXISTS` subquery. At realistic
   overdue-alert volumes (this should always be a short list — that's the point of the feature)
   it's irrelevant; if it were ever called somewhere hot with a much larger candidate set, it'd
   need to move into the query itself.

`ArticleEvent` growing without bound is the least worrying part of this schema at 100x — every
read of it is scoped to one article via an indexed FK, so the table's total size doesn't affect
any individual timeline's query cost.
