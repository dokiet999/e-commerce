from django.urls import path, re_path
from proxy.views import proxy_view

urlpatterns = [
    re_path(r'^api/(?P<service_prefix>[a-z]+)/(?P<path>.*)$', proxy_view, name='proxy'),
]
