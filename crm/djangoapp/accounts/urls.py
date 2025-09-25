from django.urls import path
from .views import CollaboratorLoginView, CollaboratorLogoutView

app_name = 'accounts'

urlpatterns = [
    path("login/", CollaboratorLoginView.as_view(), name="login"),
    path("logout/", CollaboratorLogoutView.as_view(), name="logout"),
]
