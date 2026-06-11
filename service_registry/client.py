import os
from .registry import ServiceRegistry

_registry = None


def get_registry():
    global _registry
    if _registry is None:
        _registry = ServiceRegistry(
            redis_host=os.environ.get('REDIS_HOST', 'localhost'),
            redis_port=int(os.environ.get('REDIS_PORT', 6379)),
        )
    return _registry


def register_service(service_name, host, port):
    get_registry().register(service_name, host, port)


def discover_service(service_name):
    return get_registry().get_service_url(service_name)
