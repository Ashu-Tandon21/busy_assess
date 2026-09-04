from django.contrib import admin

from .models import Article, ArticleAlertDismissal, ArticleEvent


class ArticleEventInline(admin.TabularInline):
    model = ArticleEvent
    extra = 0
    readonly_fields = ["event_type", "old_status", "new_status", "actor", "note", "created_at"]
    can_delete = False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ["title", "section", "author", "status", "publish_at", "updated_at"]
    list_filter = ["status", "section"]
    search_fields = ["title", "body"]
    inlines = [ArticleEventInline]


@admin.register(ArticleEvent)
class ArticleEventAdmin(admin.ModelAdmin):
    list_display = ["article", "event_type", "old_status", "new_status", "actor", "created_at"]
    list_filter = ["event_type"]

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(ArticleAlertDismissal)
class ArticleAlertDismissalAdmin(admin.ModelAdmin):
    list_display = ["article", "publish_at", "dismissed_by", "dismissed_at"]
