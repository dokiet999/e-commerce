from django.urls import path, include

urlpatterns = [
    path('api/coupons/', include('coupons.urls')),
]
