from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'notifications'

    def ready(self):
        import os
        if os.environ.get('RUN_MAIN') == 'true':
            try:
                from service_registry.registry import ServiceRegistry
                from django.conf import settings

                registry = ServiceRegistry()
                registry.register(
                    settings.SERVICE_NAME,
                    settings.SERVICE_HOST,
                    settings.SERVICE_PORT,
                )
            except Exception:
                pass
