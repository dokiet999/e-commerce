from django.urls import path, include

urlpatterns = [
    path('api/inventory/', include('inventory.urls')),
]
