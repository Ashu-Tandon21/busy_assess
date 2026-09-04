from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import User


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    ordering = ["email"]
    list_display = ["email", "username", "role", "is_staff", "is_active"]
    list_filter = ["role", "is_staff", "is_active"]
    fieldsets = DjangoUserAdmin.fieldsets + (
        ("Editorial role", {"fields": ("role",)}),
    )
    add_fieldsets = DjangoUserAdmin.add_fieldsets + (
        ("Editorial role", {"fields": ("email", "role")}),
    )
