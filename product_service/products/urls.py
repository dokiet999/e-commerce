from django.urls import path
from . import views

urlpatterns = [
    path('', views.product_list, name='product_list'),
    path('<int:pk>/', views.product_detail, name='product_detail'),
    path('computers/', views.computer_list, name='computer_list'),
    path('computers/<int:pk>/', views.computer_detail, name='computer_detail'),
    path('laptops/', views.computer_list, name='laptop_list'),
    path('laptops/<int:pk>/', views.computer_detail, name='laptop_detail'),
    path('mobiles/', views.mobile_list, name='mobile_list'),
    path('mobiles/<int:pk>/', views.mobile_detail, name='mobile_detail'),
    path('smartphones/', views.mobile_list, name='smartphone_list'),
    path('smartphones/<int:pk>/', views.mobile_detail, name='smartphone_detail'),
    path('clothes/', views.clothes_list, name='clothes_list'),
    path('clothes/<int:pk>/', views.clothes_detail, name='clothes_detail'),
    path('categories/', views.category_list, name='category_list'),
    path('subcategories/', views.subcategory_list, name='subcategory_list'),
    path('subcategories/<int:pk>/', views.subcategory_detail, name='subcategory_detail'),
    path('health/', views.health, name='health'),
]
