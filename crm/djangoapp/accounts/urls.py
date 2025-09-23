from django.urls import path
from .views import CollaboratorLoginView, CollaboratorLogoutView

urlpatterns = [
    path("login/", CollaboratorLoginView.as_view(), name="login"),
    path("logout/", CollaboratorLogoutView.as_view(), name="logout"),
]
