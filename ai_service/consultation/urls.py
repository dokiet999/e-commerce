from django.urls import path
from . import views

urlpatterns = [
    path('chat/', views.chat, name='chat'),
    path('chat/history/', views.chat_history, name='chat_history'),
    path('chat/clear/', views.clear_chat, name='clear_chat'),
]
