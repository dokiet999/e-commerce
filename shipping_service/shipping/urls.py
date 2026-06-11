from django.urls import path
from . import views

urlpatterns = [
    path('methods/', views.shipping_methods, name='shipping_methods'),
    path('calculate/', views.calculate_shipping, name='calculate_shipping'),
    path('', views.create_shipment, name='create_shipment'),
    path('<str:tracking_number>/track/', views.track_shipment, name='track_shipment'),
    path('<int:shipment_id>/status/', views.update_shipment_status, name='update_shipment_status'),
    path('health/', views.health, name='health'),
]
