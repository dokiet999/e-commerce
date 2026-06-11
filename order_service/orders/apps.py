from django.apps import AppConfig


class OrdersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'orders'

    def ready(self):
        import os
        if os.environ.get('RUN_MAIN') == 'true':
            try:
                from service_registry.client import register_service
                from django.conf import settings
                register_service(settings.SERVICE_NAME, settings.SERVICE_HOST, settings.SERVICE_PORT)
            except Exception:
                pass
