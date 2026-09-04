from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View
from django.views.generic import CreateView, UpdateView

from accounts.mixins import EditorRequiredMixin

from .forms import AssignWriterForm, SectionForm
from .models import Section, SectionAssignment
from .services import visible_sections


def _get_visible_section_or_404(user, pk):
    section = get_object_or_404(visible_sections(user, include_archived=True), pk=pk)
    return section


@login_required
def section_list(request):
    show_archived = request.user.is_editor and request.GET.get("archived") == "1"
    sections = (
        visible_sections(request.user, include_archived=show_archived)
        .select_related("owning_editor")
        .annotate(article_count=Count("articles", distinct=True))
    )
    return render(
        request,
        "sections/list.html",
        {"sections": sections, "show_archived": show_archived},
    )


@login_required
def section_detail(request, pk):
    section = _get_visible_section_or_404(request.user, pk)
    writers = section.writers.order_by("email")
    articles = section.articles.select_related("author").order_by("-updated_at")[:25]
    assign_form = AssignWriterForm(section=section) if request.user.is_editor else None
    return render(
        request,
        "sections/detail.html",
        {
            "section": section,
            "writers": writers,
            "articles": articles,
            "assign_form": assign_form,
        },
    )


class SectionCreateView(EditorRequiredMixin, CreateView):
    model = Section
    form_class = SectionForm
    template_name = "sections/form.html"

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f"Section “{self.object.name}” created.")
        return response

    def get_success_url(self):
        return reverse("sections:detail", args=[self.object.pk])


class SectionUpdateView(EditorRequiredMixin, UpdateView):
    model = Section
    form_class = SectionForm
    template_name = "sections/form.html"

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f"Section “{self.object.name}” updated.")
        return response

    def get_success_url(self):
        return reverse("sections:detail", args=[self.object.pk])


class SectionArchiveToggleView(EditorRequiredMixin, View):
    def post(self, request, pk):
        section = get_object_or_404(Section, pk=pk)
        section.is_archived = not section.is_archived
        section.save(update_fields=["is_archived"])
        verb = "archived" if section.is_archived else "restored"
        messages.success(request, f"Section “{section.name}” {verb}.")
        return redirect("sections:detail", pk=section.pk)


class AssignWriterView(EditorRequiredMixin, View):
    def post(self, request, pk):
        section = get_object_or_404(Section, pk=pk)
        form = AssignWriterForm(request.POST, section=section)
        if form.is_valid():
            SectionAssignment.objects.get_or_create(
                section=section, user=form.cleaned_data["writer"]
            )
            messages.success(
                request, f"{form.cleaned_data['writer'].email} assigned to {section.name}."
            )
        else:
            messages.error(request, "Could not assign that writer.")
        return redirect("sections:detail", pk=section.pk)


class RemoveWriterView(EditorRequiredMixin, View):
    def post(self, request, pk, user_id):
        section = get_object_or_404(Section, pk=pk)
        SectionAssignment.objects.filter(section=section, user_id=user_id).delete()
        messages.success(request, "Writer removed from section.")
        return redirect("sections:detail", pk=section.pk)
