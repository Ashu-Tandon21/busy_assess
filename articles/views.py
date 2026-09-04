import csv

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View
from django.views.generic import CreateView

from accounts.mixins import EditorRequiredMixin
from sections.services import visible_sections

from . import services
from .forms import ArticleForm, BulkActionForm, CommentForm, ScheduleForm
from .models import Article


def _get_visible_article_or_404(user, pk):
    return get_object_or_404(services.visible_articles(user), pk=pk)


@login_required
def dashboard(request):
    stats = services.dashboard_stats()
    return render(request, "articles/dashboard.html", {"stats": stats})


@login_required
def article_list(request):
    q = request.GET.get("q", "").strip()
    section = request.GET.get("section") or None
    status = request.GET.get("status") or None
    author = request.GET.get("author") or None
    sort = request.GET.get("sort", "updated")

    results = services.search_articles(
        request.user, q=q, section=section, status=status, author=author, sort=sort
    )
    paginator = Paginator(results, 20)
    page_obj = paginator.get_page(request.GET.get("page"))

    context = {
        "page_obj": page_obj,
        "q": q,
        "section": section,
        "status": status,
        "author": author,
        "sort": sort,
        "total_count": paginator.count,
        "sections": visible_sections(request.user, include_archived=True),
        "statuses": Article.Status.choices,
        "authors": services.visible_articles(request.user)
        .values_list("author_id", "author__email")
        .distinct()
        .order_by("author__email"),
        "bulk_form_action": reverse("articles:bulk_action"),
    }
    return render(request, "articles/list.html", context)


@login_required
def article_detail(request, pk):
    article = _get_visible_article_or_404(request.user, pk)
    if request.method == "POST":
        form = CommentForm(request.POST)
        if form.is_valid():
            try:
                services.add_comment(article, actor=request.user, text=form.cleaned_data["text"])
                messages.success(request, "Comment added.")
                return redirect("articles:detail", pk=article.pk)
            except services.TransitionError as exc:
                messages.error(request, str(exc))
    else:
        form = CommentForm()

    timeline = article.events.select_related("actor").all()
    revisions = article.revisions.order_by("-created_at")
    schedule_form = ScheduleForm()
    return render(
        request,
        "articles/detail.html",
        {
            "article": article,
            "timeline": timeline,
            "revisions": revisions,
            "comment_form": form,
            "schedule_form": schedule_form,
            "can_edit": services.can_edit(article, request.user),
        },
    )


class ArticleCreateView(LoginRequiredMixin, CreateView):
    model = Article
    form_class = ArticleForm
    template_name = "articles/form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        initial_section = self.request.GET.get("section")
        if initial_section and self.request.method == "GET":
            kwargs["initial"] = {"section": initial_section}
        return kwargs

    def form_valid(self, form):
        try:
            self.object = services.create_article(
                title=form.cleaned_data["title"],
                body=form.cleaned_data["body"],
                section=form.cleaned_data["section"],
                author=self.request.user,
            )
        except services.TransitionError as exc:
            form.add_error(None, str(exc))
            return self.form_invalid(form)
        messages.success(self.request, "Article created as a Draft.")
        return redirect("articles:detail", pk=self.object.pk)


@login_required
def article_edit(request, pk):
    article = _get_visible_article_or_404(request.user, pk)
    if not services.can_edit(article, request.user):
        messages.error(request, "You cannot edit this article.")
        return redirect("articles:detail", pk=article.pk)

    if request.method == "POST":
        form = ArticleForm(request.POST, instance=article, user=request.user)
        if form.is_valid():
            try:
                services.edit_article(
                    article,
                    title=form.cleaned_data["title"],
                    body=form.cleaned_data["body"],
                    editor=request.user,
                )
                messages.success(request, "Article updated.")
                return redirect("articles:detail", pk=article.pk)
            except services.TransitionError as exc:
                form.add_error(None, str(exc))
    else:
        form = ArticleForm(instance=article, user=request.user)
    return render(request, "articles/form.html", {"form": form, "object": article})


class _ArticleActionView(LoginRequiredMixin, View):
    """Base for the single-article lifecycle POST endpoints below."""

    service_fn = None
    success_message = "Done."

    def post(self, request, pk):
        article = _get_visible_article_or_404(request.user, pk)
        try:
            self.run(request, article)
            messages.success(request, self.success_message)
        except services.TransitionError as exc:
            messages.error(request, str(exc))
        return redirect("articles:detail", pk=article.pk)

    def run(self, request, article):
        self.service_fn(article, actor=request.user)


class SubmitView(_ArticleActionView):
    service_fn = staticmethod(services.submit_for_review)
    success_message = "Submitted for review."


class ApproveView(_ArticleActionView):
    service_fn = staticmethod(services.approve)
    success_message = "Article approved."


class PublishView(_ArticleActionView):
    service_fn = staticmethod(services.publish)
    success_message = "Article published."


class UnpublishView(_ArticleActionView):
    service_fn = staticmethod(services.unpublish)
    success_message = "Article unpublished — back to Approved."


class OpenRevisionView(LoginRequiredMixin, View):
    def post(self, request, pk):
        article = _get_visible_article_or_404(request.user, pk)
        try:
            revision = services.open_revision(article, actor=request.user)
            messages.success(request, f"Revision #{revision.pk} opened.")
            return redirect("articles:detail", pk=revision.pk)
        except services.TransitionError as exc:
            messages.error(request, str(exc))
            return redirect("articles:detail", pk=article.pk)


class ScheduleView(LoginRequiredMixin, View):
    def post(self, request, pk):
        article = _get_visible_article_or_404(request.user, pk)
        form = ScheduleForm(request.POST)
        if form.is_valid():
            try:
                services.schedule(article, actor=request.user, publish_at=form.cleaned_data["publish_at"])
                messages.success(request, "Article scheduled.")
            except services.TransitionError as exc:
                messages.error(request, str(exc))
        else:
            messages.error(request, "Enter a valid future publish time.")
        return redirect("articles:detail", pk=article.pk)


class BulkActionView(EditorRequiredMixin, View):
    def post(self, request):
        form = BulkActionForm(request.POST)
        if not form.is_valid():
            messages.error(request, "Could not run that bulk action — check your selection.")
            return redirect("articles:list")

        action = form.cleaned_data["action"]
        ids = form.cleaned_data["article_ids"]
        if action == "schedule":
            results = services.bulk_schedule(ids, actor=request.user, publish_at=form.cleaned_data["publish_at"])
        else:
            results = services.bulk_unpublish(ids, actor=request.user)

        return render(request, "articles/bulk_result.html", {"action": action, "results": results})


@login_required
def export_calendar_csv(request):
    articles = (
        services.visible_articles(request.user)
        .filter(status__in=[Article.Status.SCHEDULED, Article.Status.PUBLISHED])
        .select_related("section", "author")
        .order_by("publish_at")
    )
    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="editorial_calendar.csv"'
    writer = csv.writer(response)
    writer.writerow(["Title", "Section", "Author", "Status", "Publish At"])
    for article in articles:
        writer.writerow(
            [
                article.title,
                article.section.name,
                article.author.email,
                article.get_status_display(),
                article.publish_at.isoformat() if article.publish_at else "",
            ]
        )
    return response


@login_required
def alerts(request):
    overdue = services.overdue_articles(request.user)
    return render(request, "articles/alerts.html", {"overdue": overdue})


class DismissAlertView(EditorRequiredMixin, View):
    def post(self, request, pk):
        article = get_object_or_404(Article, pk=pk)
        try:
            services.dismiss_alert(article, actor=request.user)
            messages.success(request, "Alert dismissed.")
        except services.TransitionError as exc:
            messages.error(request, str(exc))
        return redirect("articles:alerts")
