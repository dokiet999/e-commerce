from django.urls import path, include

urlpatterns = [
    path('api/ai/', include('behavior.urls')),
    path('api/ai/', include('consultation.urls')),
    path('api/ai/', include('recommendations.urls')),
]
