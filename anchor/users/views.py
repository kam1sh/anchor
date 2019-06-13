from allauth.account.views import LoginView as AllauthLogin
from allauth.account.forms import SignupForm
from django.contrib import auth
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse
from django.views.generic import DetailView, ListView, RedirectView, UpdateView


User = auth.get_user_model()


class LoginView(AllauthLogin):
    template_name = "account/base-sign.html"
    signup_form = SignupForm

    def render_to_response(self, context, **kwargs):
        context["signup_form"] = self.signup_form()
        return super().render_to_response(context, **kwargs)


class UserDetailView(LoginRequiredMixin, DetailView):

    model = User
    slug_field = "username"
    slug_url_kwarg = "username"


user_detail_view = UserDetailView.as_view()


@auth.decorators.login_required
def current_user(request):
    return user_detail_view(request, username=request.user.username)


class UserListView(LoginRequiredMixin, ListView):

    model = User
    slug_field = "username"
    slug_url_kwarg = "username"


user_list_view = UserListView.as_view()


class UserUpdateView(LoginRequiredMixin, UpdateView):

    model = User
    fields = ["name"]

    def get_success_url(self):
        return reverse("users:details", kwargs={"username": self.request.user.username})

    def get_object(self):
        return User.objects.get(username=self.request.user.username)


user_update_view = UserUpdateView.as_view()


class UserRedirectView(LoginRequiredMixin, RedirectView):

    permanent = False

    def get_redirect_url(self):
        return (
            "/"
        )  # reverse("users:details", kwargs={"username": self.request.user.username})


user_redirect_view = UserRedirectView.as_view()
