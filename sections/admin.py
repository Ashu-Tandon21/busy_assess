from django.contrib import admin

from .models import Section, SectionAssignment


class SectionAssignmentInline(admin.TabularInline):
    model = SectionAssignment
    extra = 0


@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = ["name", "owning_editor", "is_archived", "created_at"]
    list_filter = ["is_archived"]
    search_fields = ["name", "description"]
    inlines = [SectionAssignmentInline]
