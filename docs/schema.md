# Schema

Answer each of these, in your own words.

- Table by table: what columns and types does each one have?
 >User extends Django's AbstractUser, so most standard fields come for free. I added email as unique, since that's the actual login field, and a role field that's either editor or writer.
->Section has a name, a description, an owning_editor foreign key protected on delete, is_archived, and created_at.
->SectionAssignment is the through table linking writers to sections, with a foreign key to each side, a created_at, and a unique constraint on the pair so nobody gets assigned twice.
->Article has title, body, an author and section foreign key both protected, a status field indexed since it's filtered on constantly, a nullable indexed publish_at, created_at and updated_at, and a revision_of field pointing back at another article when this row is a revision of it.
->ArticleEvent is the append only timeline, with a foreign key to the article, an event_type,  and new status filled in only for status changes, an actor, a note field, and an indexed create-at.
->ArticleAlertDismissal has a foreign key to the article, a publish_at that's a copy of what the article had at dismissal time rather than a live pointer, a dismissed-by restricted to editors, and a unique constraint on article and publish-at together.

- Which relationships are one-to-many, and which are many-to-many?
 >Almost everything here is one to many, one editor owns many sections, one author writes many articles, one section holds many articles, one article has many timeline events. Articles also point back at themselves through revision-of for revisions. The one real many to many is sections and writers, and I used an actual through model for that instead of a plain ManyToManyField so I had somewhere to put a created_at and enforce no duplicate pairing.

- Which constraints are enforced by the database, and which by application code — and why did you draw the line there?
 >The database enforces the stuff that's cheap to guarantee once and easy to accidentally miss in code, email uniqueness, the section and user pair being unique, the alert dismissal pair being unique, and the foreign key rules. Everything about the actual lifecycle sits in services.py instead, every transition rule, who can do what, and the append only behaviour on ArticleEvent, which I enforced at the model level by making save and delete raise once a row exists. I split it this way because the lifecycle rules have a lot of branching and specific messages attached that really belong in one readable place, and having one services module per app is what made sure every view enforces the rule the same way instead of drifting apart over time.

- What did you deliberately denormalise?
 >The publish_at on ArticleAlertDismissal is a copy, not a live reference. If an article gets unpublished and rescheduled for a new time, the old dismissal shouldn't silence the new overdue alert, since it's really a different situation now. Copying the timestamp at dismissal time made that distinction basically free instead of needing extra logic to tell the two cases apart.

- What would break first if this had 100x the data?
 >Search would go first, it's just an icontains filter on title and body, which is an unindexed scan, so at 100x the rows every search becomes a full table scan. Postgres full text search with a proper index would fix that. Right behind it is the overdue alerts function, which pulls matching articles into python and checks them against dismissals with a python set instead of doing that exclusion in the database, fine now but wasteful at real scale.
