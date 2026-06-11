from django.urls import path
from . import views

urlpatterns = [
    path('', views.order_list, name='order_list'),
    path('<int:order_id>/', views.order_detail, name='order_detail'),
    path('<int:order_id>/status/', views.update_status, name='update_status'),
    path('<int:order_id>/cancel/', views.cancel_order, name='cancel_order'),
    path('health/', views.health, name='health'),
]
