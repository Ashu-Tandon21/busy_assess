from django.urls import path

from . import views

app_name = "articles"

urlpatterns = [
    path("", views.article_list, name="list"),
    path("new/", views.ArticleCreateView.as_view(), name="create"),
    path("bulk/", views.BulkActionView.as_view(), name="bulk_action"),
    path("export/calendar.csv", views.export_calendar_csv, name="export_calendar"),
    path("alerts/", views.alerts, name="alerts"),
    path("alerts/<int:pk>/dismiss/", views.DismissAlertView.as_view(), name="dismiss_alert"),
    path("<int:pk>/", views.article_detail, name="detail"),
    path("<int:pk>/edit/", views.article_edit, name="edit"),
    path("<int:pk>/submit/", views.SubmitView.as_view(), name="submit"),
    path("<int:pk>/approve/", views.ApproveView.as_view(), name="approve"),
    path("<int:pk>/schedule/", views.ScheduleView.as_view(), name="schedule"),
    path("<int:pk>/publish/", views.PublishView.as_view(), name="publish"),
    path("<int:pk>/unpublish/", views.UnpublishView.as_view(), name="unpublish"),
    path("<int:pk>/revise/", views.OpenRevisionView.as_view(), name="open_revision"),
]
