from django.urls import path, include

urlpatterns = [
    path('api/shipping/', include('shipping.urls')),
]
