import logging
from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Index knowledge base documents into ChromaDB'

    def add_arguments(self, parser):
        parser.add_argument(
            '--source',
            type=str,
            choices=['all', 'docs', 'products'],
            default='all',
            help='What to index: all, docs, or products',
        )

    def handle(self, *args, **options):
        logging.basicConfig(level=logging.INFO)
        from kb.indexer import index_all, index_documents, index_products

        source = options['source']

        if source == 'docs':
            count = index_documents()
            self.stdout.write(self.style.SUCCESS(f"Indexed {count} document chunks"))
        elif source == 'products':
            count = index_products()
            self.stdout.write(self.style.SUCCESS(f"Indexed {count} product chunks"))
        else:
            count = index_all()
            self.stdout.write(self.style.SUCCESS(f"Indexed {count} total chunks"))
