from django.urls import path
from . import views

urlpatterns = [
    path('', views.review_list, name='review_list'),
    path('<int:review_id>/', views.review_detail, name='review_detail'),
    path('product/<int:product_id>/', views.product_reviews, name='product_reviews'),
    path('product/<int:product_id>/summary/', views.product_review_summary, name='product_review_summary'),
    path('health/', views.health, name='health'),
]
