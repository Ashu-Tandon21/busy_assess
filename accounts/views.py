from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.generic import CreateView

from .forms import UserCreateForm
from .mixins import EditorRequiredMixin
from .models import User


@login_required
def user_list(request):
    users = User.objects.order_by("email")
    return render(request, "accounts/user_list.html", {"users": users})


class UserCreateView(EditorRequiredMixin, CreateView):
    """Lets an editor add a new account to the roster.

    There's no public signup — see docs/architecture.md ("No user
    self-signup"). Only editors can reach this view.
    """

    model = User
    form_class = UserCreateForm
    template_name = "accounts/user_form.html"
    success_url = reverse_lazy("accounts:user_list")

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f"Account created for {self.object.email}.")
        return response