from django.urls import path
from . import views

urlpatterns = [
    path('recommendations/personalized/', views.personalized, name='rec-personalized'),
    path('recommendations/similar/<int:product_id>/', views.similar, name='rec-similar'),
    path('recommendations/also-bought/<int:product_id>/', views.also_bought, name='rec-also-bought'),
    path('recommendations/trending/', views.trending, name='rec-trending'),
    path('recommendations/cart/', views.cart_recommendations, name='rec-cart'),
    path('recommendations/search/', views.search_recommendations, name='rec-search'),
    path('recommendations/next-product/', views.next_product, name='rec-next-product'),
    path('recommendations/health/', views.rec_health, name='rec-health'),
]
