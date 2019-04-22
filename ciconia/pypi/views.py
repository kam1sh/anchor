from django.shortcuts import render
from django.views.generic import View, DetailView

from .models import PythonPackage

# Create your views here.


class PackageList(View):
    model = PythonPackage
    template_name = "packages.html"

    def get(self, request):
        context = {
            "packages": []
        }
        return render(request, self.template_name, context)