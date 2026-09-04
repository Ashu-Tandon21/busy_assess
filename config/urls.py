"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
"""
from django.contrib import admin
from django.urls import include, path

from articles.views import dashboard

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("sections/", include("sections.urls")),
    path("articles/", include("articles.urls")),
    path("", dashboard, name="dashboard"),
]
