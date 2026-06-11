import requests as http_requests
from django.http import JsonResponse
from django.conf import settings
from service_registry.client import discover_service


def _get_service_url(service_name):
    """Try service registry first, fallback to configured URL."""
    try:
        url = discover_service(service_name)
        if url:
            return url
    except Exception:
        pass
    return settings.SERVICE_URLS.get(service_name)


def proxy_view(request, service_prefix, path):
    """Proxy requests to the appropriate microservice."""
    service_name = settings.ROUTE_MAP.get(service_prefix)
    if not service_name:
        return JsonResponse({'error': 'Service not found'}, status=404)

    service_url = _get_service_url(service_name)
    if not service_url:
        return JsonResponse({'error': 'Service unavailable'}, status=503)

    # Build target URL
    target_url = f"{service_url}/api/{service_prefix}/{path}"
    if not target_url.endswith('/'):
        target_url += '/'

    # Build headers to forward
    headers = {
        'Content-Type': request.content_type or 'application/json',
    }

    # Forward Authorization header
    auth_header = request.META.get('HTTP_AUTHORIZATION')
    if auth_header:
        headers['Authorization'] = auth_header

    # Forward user identity
    user_id = getattr(request, '_gateway_user_id', None)
    if user_id:
        headers['X-User-Id'] = str(user_id)
    role = getattr(request, '_gateway_role', None)
    if role:
        headers['X-Role'] = role

    # Forward validated service identity for service-only gateway calls.
    service_token = request.META.get('HTTP_X_SERVICE_TOKEN')
    caller_service_name = request.META.get('HTTP_X_SERVICE_NAME')
    if service_token:
        headers['X-Service-Token'] = service_token
    if caller_service_name:
        headers['X-Service-Name'] = caller_service_name

    # Forward session_id for guest cart
    session_id = getattr(request, '_gateway_session_id', None)
    if session_id:
        headers['X-Session-Id'] = session_id

    # AI service needs longer timeout for LLM calls
    timeout = 300 if service_name == 'ai_service' else 10

    try:
        resp = http_requests.request(
            method=request.method,
            url=target_url,
            headers=headers,
            data=request.body if request.body else None,
            timeout=timeout,
            allow_redirects=False,
        )

        # Build Django response
        try:
            response_data = resp.json()
            django_response = JsonResponse(response_data, status=resp.status_code, safe=False)
        except ValueError:
            django_response = JsonResponse(
                {'detail': resp.text},
                status=resp.status_code,
            )

        # Copy session_id cookie if set by SessionIdMiddleware
        return django_response

    except http_requests.ConnectionError:
        return JsonResponse({'error': f'Service {service_prefix} is unavailable'}, status=503)
    except http_requests.Timeout:
        return JsonResponse({'error': f'Service {service_prefix} timed out'}, status=504)
