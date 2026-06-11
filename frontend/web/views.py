from django.shortcuts import render
from django.conf import settings


def _ctx(extra=None):
    ctx = {'api_url': settings.API_GATEWAY_URL}
    if extra:
        ctx.update(extra)
    return ctx


def home(request):
    return render(request, 'home.html', _ctx())


def product_detail(request, product_id):
    return render(request, 'product_detail.html', _ctx({'product_id': product_id}))


def cart(request):
    return render(request, 'cart.html', _ctx())


def login_page(request):
    return render(request, 'login.html', _ctx())


def register_page(request):
    return render(request, 'register.html', _ctx())


def profile(request):
    return render(request, 'profile.html', _ctx())


def chat_page(request):
    return render(request, 'chat.html', _ctx())
