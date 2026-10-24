from django.contrib.auth import views as auth_views
from django.urls import path

from . import views

app_name = "contractors"

urlpatterns = [
    path("", views.home, name="home"),
    path("contractors/", views.contractor_list, name="list"),
    path("contractors/<int:pk>/", views.contractor_detail, name="detail"),
    path("contractors/<int:pk>/quote/", views.quote_request, name="quote_request"),
    path("contractors/<int:pk>/review/", views.review_edit, name="review_edit"),
    path("signup/", views.signup, name="signup"),
    path(
        "login/",
        auth_views.LoginView.as_view(
            template_name="contractors/login.html",
            redirect_authenticated_user=True,
        ),
        name="login",
    ),
    path("logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("my-requests/", views.my_requests, name="my_requests"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("dashboard/profile/", views.profile_edit, name="profile_edit"),
    path("dashboard/projects/add/", views.project_edit, name="project_add"),
    path("dashboard/projects/<int:pk>/edit/", views.project_edit, name="project_edit"),
    path("dashboard/projects/<int:pk>/delete/", views.project_delete, name="project_delete"),
    path("dashboard/requests/", views.contractor_requests, name="contractor_requests"),
    path("dashboard/requests/<int:pk>/", views.request_respond, name="request_respond"),
    path("dashboard/verification/", views.verification, name="verification"),
    path("dashboard/verification/<int:pk>/delete/", views.verification_delete, name="verification_delete"),
    path("staff/verification-file/<int:pk>/", views.verification_file, name="verification_file"),
]