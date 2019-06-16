from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse
from django.views.generic import DetailView, ListView, RedirectView, UpdateView

from .models import Package


class Index(ListView):
    model = Package
    template_name = "pages/home.html"

    def get_queryset(self):
        """
        Returns list of packages that current user owns,
        otherwise list of public packages.
        """
        if self.request.user.is_authenticated:
            return self.model.objects.filter(owner=self.request.user)
        else:
            return self.model.objects.filter(public=True)
