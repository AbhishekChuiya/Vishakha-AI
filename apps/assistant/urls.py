from django.urls import path
from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("api/chat/", views.chat, name="chat"),
    path("api/chat/state/", views.chat_state, name="chat_state"),
    path("api/chat/new/", views.new_chat, name="new_chat"),
]