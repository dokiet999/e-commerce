from django.urls import path
from . import views

urlpatterns = [
    path('validate/', views.validate_coupon, name='validate_coupon'),
    path('apply/', views.apply_coupon, name='apply_coupon'),
    path('', views.coupon_list, name='coupon_list'),
    path('<int:coupon_id>/', views.coupon_detail, name='coupon_detail'),
    path('health/', views.health, name='health'),
]
