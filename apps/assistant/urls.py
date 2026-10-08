from django.urls import path
from . import views

urlpatterns = [
    path("accounts/", views.account_chooser, name="account_chooser"),
    path("accounts/add/", views.account_add, name="account_add"),
    path("accounts/switch/", views.account_switch, name="account_switch"),
    path("accounts/remove/", views.account_remove, name="account_remove"),
    path(
    "login/",
    views.login_view,
    name="login"
    ),
    path(
    "logout/",
    views.logout_view,
    name="logout"
    ),
    path(
    "signup/",
    views.signup_view,
    name="signup"
    ),
    path("", views.home, name="home"),
    path("api/chat/", views.chat, name="chat"),
    path("api/chat/state/", views.chat_state, name="chat_state"),
    path("api/chat/new/", views.new_chat, name="new_chat"),
    path(
    "api/chat/delete/",
    views.delete_chat,
    name="delete_chat"
    ),
    path(
        "api/chat/stop/",
        views.stop_chat,
        name="stop_chat"
    ),
]