from django.urls import path, include

urlpatterns = [
    path('api/reviews/', include('reviews.urls')),
]
