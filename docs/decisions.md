# Decisions

Log the decisions that actually shaped this codebase — the ones where a real alternative existed and
you picked one. At least five entries. For each: what you chose, what you rejected, and why. At least
one entry must be a decision you later reversed — say what changed your mind. It can be any entry
below, not necessarily the last one; add a **Later reversed:** line to whichever one it is.

## Decision 1

Chose: Server rendered Django templates with Bootstrap instead of a separate frontend.
Rejected: A React or Vue frontend talking to a JSON api.
Why: The app is mostly forms, lists and status changes, not something that needed to feel like a single page app, so one deployable thing made more sense than two plus the auth plumbing between them.

## Decision 2

Chose: Putting all lifecycle and query logic in a services.py module per app, keeping views thin.
Rejected: Writing permission checks and status changes directly inside each view.
Why: The brief needs role rules enforced on the server, not just hidden in the UI. One function per transition means every view goes through the exact same rule instead of quietly drifting apart.

## Decision 3

Chose: Logging in with email instead of a username.
Rejected: Django's default username based login.
Why: People think of their account as their email, and the brief describes signing in with email and password. Username still exists since Django's auth expects it, but it's not what you log in with.

## Decision 4

Chose: Making the ArticleEvent timeline append only at the model level, even for editors.
Rejected: A normal editable model, assuming nobody would build an edit path for it later.
Why: The brief says nothing in the timeline can be edited or deleted after the fact. Blocking it at the model level means that holds no matter what code touches this model later, not just what exists today.

## Decision 5

Chose: Storing writer to section assignments in an explicit through model. Later reversed: I started with a plain ManyToManyField, the obvious first move, and switched to a through model once I needed a created_at on the assignment and a way to stop duplicate assignments at the database level.
Rejected: Keeping the plain field and tracking the assignment date some other way.
Why: A through model with its own unique constraint enforces no duplicate assignment at the database level instead of relying on code to check first, and gave me a natural place for created_at.

## Decision 6

Chose: No public self signup, accounts get created by an editor through a gated page.
Rejected: A normal open signup form.
Why: The brief describes a roster based newsroom where editors assign writers, not the other way around. Open signup would let anyone register as an editor. Reusing the same EditorRequiredMixin meant no separate rules just for this one page.
