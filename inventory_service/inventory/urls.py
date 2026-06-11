from django.urls import path
from . import views

urlpatterns = [
    path('<int:product_id>/', views.inventory_detail, name='inventory_detail'),
    path('reserve/', views.reserve_stock, name='reserve_stock'),
    path('release/', views.release_stock, name='release_stock'),
    path('deduct/', views.deduct_stock, name='deduct_stock'),
    path('restock/', views.restock, name='restock'),
    path('low-stock/', views.low_stock, name='low_stock'),
    path('health/', views.health, name='health'),
]
