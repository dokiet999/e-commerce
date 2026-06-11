from django.urls import path
from . import views

urlpatterns = [
    path('', views.payment_list, name='payment_list'),
    path('<int:payment_id>/', views.payment_detail, name='payment_detail'),
    path('<int:payment_id>/refund/', views.refund_payment, name='refund_payment'),
    path('health/', views.health, name='health'),
]
