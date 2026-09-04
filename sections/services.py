"""Server-side section visibility rules.

Both the section list and the article form need "which sections can this
user see / act in", so it lives here once rather than being re-derived (and
potentially re-derived inconsistently) in each view.
"""

from django.db.models import QuerySet

from .models import Section


def visible_sections(user, *, include_archived: bool = False) -> QuerySet[Section]:
    """Sections a user is allowed to browse.

    Editors see every section (archived ones only when asked for). Writers
    only ever see sections they are assigned to, archived or not — an
    assignment made before a section was archived is still how a writer
    finds their own past work in it.
    """
    if user.is_editor:
        qs = Section.objects.all()
        if not include_archived:
            qs = qs.filter(is_archived=False)
        return qs
    return Section.objects.filter(writers=user)


def assignable_sections(user) -> QuerySet[Section]:
    """Sections a user may create a *new* article in.

    Editors can write into any non-archived section; writers only into
    sections they are currently assigned to and that are not archived.
    """
    if user.is_editor:
        return Section.objects.filter(is_archived=False)
    return Section.objects.filter(writers=user, is_archived=False)
