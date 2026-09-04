# Plan

## How did you split the work into sessions?

Honestly, not across a week — the scaffold (models, migrations, project structure) already
existed from an earlier session, and everything else in this repository (services, views,
templates, tests, docs, deploy config) was built in one continuous AI-assisted sitting on
2026-09-02, working through the ten goals in order rather than in the roughly-2-hours-a-day
cadence the brief suggests. That's a real gap from how the brief asks this to be paced, and it's
worth saying plainly rather than dressing the commit history up as something it isn't. What *is*
true to the brief: the commits below are grouped by what was actually built and in what order,
each one runnable and tested on its own, not one "finished app" commit at the end.

## What order did you build in, and why that order?

1. **Config first** (`SQLite locally, prod-ready settings`) — before writing any feature, get
   `manage.py check`/`test`/`runserver` working against the existing scaffold, and get the
   local/production database split settled, since every later step depends on being able to run
   the app.
2. **Accounts → Sections → Articles**, in dependency order — `Article` FKs into `Section` and
   `User`, `Section` FKs into `User`, so building bottom-up meant every layer had something real
   to import rather than stubbing interfaces I'd have to guess at twice.
3. **`articles/services.py` before `articles/views.py`** — goal #4's transition rules are the
   part of this brief with exact, checkable rules ("what happens on an illegal move" is stated
   outright), so getting those right as pure functions I could unit-test directly, before any
   HTTP/template layer existed to obscure a wrong result, mattered more here than in the more
   straightforward CRUD apps.
4. **Templates and manual click-through last, tests alongside services** — the lifecycle rules
   got unit tests as they were written; the UI got a manual pass (log in as each role, run every
   button) once the pages existed, which is what caught the bulk-action bug in `decisions.md`
   #6 — that class of bug doesn't show up in a service-layer test at all.
5. **Docs and deploy config after the app worked**, not from memory at the end in the sense the
   brief warns against, but genuinely last in this session — because `architecture.md` and
   `schema.md` describe decisions (the services split, the denormalisation trade-offs) that
   weren't fully settled until the code existed to describe.

## What did you estimate versus what it actually took?

No hour-by-hour estimate was made going in, for the reason above — this wasn't paced as a
multi-day effort with checkpoints, so there isn't a real "estimated vs. actual" to report
honestly. If you're reading this before the call: budget time to actually read through
`articles/services.py` and the test file end to end before it, since that's where nearly all of
the actual judgement calls in this submission live, and you should be able to defend each of
them as your own.

## What did you cut when you ran short?

Nothing from the required ten was cut — all ten are implemented and covered by the test suite
(`python manage.py test`, 50 tests, all green as of the last commit). What's genuinely missing:

- **No stretch goal.** None of the nine optional ideas in the brief were attempted — the ten
  required goals used the full scope of this session.
- **No load/performance testing** of the "100x the data" question in `schema.md` — that section
  is reasoned from the query shapes, not measured against a seeded 100x dataset, which would be
  the obvious next step with more time.
- **Deployment is prepared, not executed** — `build.sh`, `Procfile`, and `render.yaml` are
  written and the settings are production-ready (see `config/settings.py`'s `DEBUG=False`
  branch), but standing up the actual Supabase project and Render service, and filling in the
  live URL and demo credentials in `SUBMISSION.md`, needs real accounts and hasn't happened yet.
