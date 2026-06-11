from django.urls import path
from . import views

urlpatterns = [
    path('events/', views.record_event, name='record_event'),
    path('events/list/', views.get_events, name='get_events'),
    path('profile/', views.get_profile, name='get_profile'),
    path('health/', views.health, name='ai_health'),
]
