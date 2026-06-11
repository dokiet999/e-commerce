from django.urls import path
from . import views

urlpatterns = [
    path('', views.cart_detail, name='cart_detail'),
    path('items/', views.add_item, name='add_item'),
    path('items/<int:item_id>/', views.update_item, name='update_item'),
    path('items/<int:item_id>/remove/', views.remove_item, name='remove_item'),
    path('clear/', views.clear_cart, name='clear_cart'),
    path('merge/', views.merge_cart, name='merge_cart'),
    path('health/', views.health, name='health'),
]
