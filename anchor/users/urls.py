from django.urls import path

from anchor.users.views import (
    LoginView,
    user_detail_view,
    user_list_view,
    user_redirect_view,
    user_update_view,
)

app_name = "users"
urlpatterns = [
    path("", view=user_list_view, name="list"),
    path("login/", view=LoginView.as_view(), name="login"),
    path("~redirect/", view=user_redirect_view, name="redirect"),
    path("~update/", view=user_update_view, name="update"),
    path("current/", view=user_detail_view, name="details_current"),
    path("<str:username>/", view=user_detail_view, name="details"),
]
