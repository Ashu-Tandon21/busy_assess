from django.urls import path

from . import views

app_name = "sections"

urlpatterns = [
    path("", views.section_list, name="list"),
    path("new/", views.SectionCreateView.as_view(), name="create"),
    path("<int:pk>/", views.section_detail, name="detail"),
    path("<int:pk>/edit/", views.SectionUpdateView.as_view(), name="edit"),
    path("<int:pk>/archive/", views.SectionArchiveToggleView.as_view(), name="archive_toggle"),
    path("<int:pk>/assign/", views.AssignWriterView.as_view(), name="assign_writer"),
    path(
        "<int:pk>/assign/<int:user_id>/remove/",
        views.RemoveWriterView.as_view(),
        name="remove_writer",
    ),
]
