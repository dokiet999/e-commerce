import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ai_config.settings')

application = get_wsgi_application()

# Preload embedding model at startup to avoid cold-start delay on first chat
try:
    from kb.vector_store import get_embeddings
    get_embeddings()
except Exception:
    pass
