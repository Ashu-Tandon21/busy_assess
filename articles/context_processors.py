from . import services


def overdue_alerts(request):
    """Feeds the nav badge (goal #10) on every page, not just the alerts page."""
    if not request.user.is_authenticated:
        return {}
    return {"overdue_alert_count": len(services.overdue_articles(request.user))}
