# AI prompts

Read this section first if you're the one who has to defend this submission on a call — how it
was actually built.

## How AI was used here

This wasn't "write some code, paste it in, fix what breaks" — it was built with Claude Code (an
agentic coding CLI) operating directly on this repository: reading the existing scaffold,
writing files, running migrations, running the dev server, logging in as each role over HTTP to
click through flows, running the test suite, and committing. The prompt log below is therefore
short and high-level rather than a long back-and-forth of small snippets, because most of the
actual direction happened as one continuous agentic session working through the brief goal by
goal, not as repeated human-typed micro-prompts. That means the honesty this file is asking for
matters even more than usual: nobody should read this repository and assume a human wrote every
line by hand from scratch, and nobody should assume the person submitting it can't explain any
part of it either. Both `docs/architecture.md` and `docs/decisions.md` were written to be
something a real person can stand behind in the call the brief describes — read those before
assuming this file is the whole story.

## Getting oriented

### Prompt

> "the thing is i have to make the assessmengt as it is written/defined in readme help me make
> it"

### What I got

Before writing anything, I read the existing scaffold (a partially-built Django project: models
for `User`/`Section`/`Article`/`ArticleEvent`/`ArticleAlertDismissal` already existed, with no
views, templates, forms, tests, or docs filled in) and asked three clarifying questions rather
than guessing: server-rendered Django vs. a split API+frontend, SQLite-locally-vs-Postgres-always
for dev, and whether to actually stand up hosting now or prepare it and document the steps. All
three came back as the recommended option, which set the shape of everything that followed (see
`decisions.md` #1 and #2 for the reasoning behind those two choices).

### What I corrected

Nothing wrong yet at this stage — this was scoping, not code.

## Building the lifecycle rules (`articles/services.py`)

### Prompt

Continuation of the same session, self-directed against goal #4's exact wording — no new prompt
from the user; the brief's own text ("what happens on an illegal move... those specifics are the
actual ask") was worked through clause by clause into one function per transition
(`submit_for_review`, `approve`, `schedule`, `publish`, `unpublish`, `open_revision`,
`edit_article`), each raising `TransitionError` with the specific message for the specific rule
it's enforcing.

### What I got

A first pass that covered every transition text in the brief directly, but left one real
ambiguity: goal #4 never actually states how a `Scheduled` article becomes `Published` (the
"stamps its publish time as now" line is specific to the *immediate*-publish path from
`Approved`). Read literally, there's no described mechanism for a `Scheduled` article to ever
reach `Published` at all.

### What I corrected

I resolved this by reasoning from goal #10 instead of guessing: if `Scheduled` → `Published`
happened automatically when `publish_at` arrived, an article could never actually be *overdue*
(goal #10's whole premise), so it has to be a manual action — the same "Publish now" control
already used for the immediate-publish case, now also legal from `Scheduled`. That reasoning is
recorded as `decisions.md` #4, since it's a real interpretive call a reviewer might ask about
directly.

## Testing against the running app, not just the service layer

### Prompt

Self-directed: after the views and templates existed, log in as an editor and a writer over real
HTTP requests (not just `TestCase`) and exercise the actual flows — search/filter, an illegal
transition, a bulk action, the CSV export, the alerts page.

### What I got

Most flows worked on the first pass. The bulk-schedule flow did not: submitting a selection of
several checked articles only ever scheduled the last one in the list.

### What I corrected

The bug was a `name` attribute collision — see `decisions.md` #6 for the full explanation. This
was caught and fixed *before* it was ever presented as working, by actually running the server
and clicking through the feature rather than trusting that the unit tests (which called
`services.bulk_schedule()` directly, correctly, and would never have caught an HTML form bug)
were sufficient proof the feature worked end to end. It's the one case in this session where
"what I got" was visibly wrong and the fix is traceable in that decision entry rather than just
silently folded into the final diff.

## Docs and deploy prep

### Prompt

Self-directed, from the `docs/*.md` stub questions and the README's hosting section directly —
each stub's bullet points were answered in order against the actual code that existed by that
point, not from a plan written before the code did.

### What I got / corrected

`docs/plan.md` is the one document here that required a genuine correction of framing rather
than content: the brief expects incremental work paced across roughly a week, and this was built
in one continuous session instead. Rather than write a plan implying a pace that didn't happen,
`plan.md` says so directly. That's the most important thing this file can model — the instruction
not to submit something you can't explain applies just as much to the *process* claims in `docs/`
as it does to the code.
