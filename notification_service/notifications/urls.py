from django.urls import path
from . import views

urlpatterns = [
    path('health/', views.health, name='notification_health'),
    path('', views.notification_list, name='notification_list'),
    path('unread-count/', views.unread_count, name='notification_unread_count'),
    path('mark-all-read/', views.mark_all_read_view, name='notification_mark_all_read'),
    path('<str:notification_id>/', views.notification_detail, name='notification_detail'),
    path('<str:notification_id>/read/', views.mark_read, name='notification_mark_read'),
]
