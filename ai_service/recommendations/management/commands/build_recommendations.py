"""
Management command to build/rebuild the recommendation data.
Precomputes co-occurrence matrix and product similarity pairs.
"""

from django.core.management.base import BaseCommand

from recommendations.collaborative import build_co_occurrence_matrix
from recommendations.content_based import build_similarity_matrix, clear_product_cache


class Command(BaseCommand):
    help = 'Build recommendation data (co-occurrence matrix and similarity pairs)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--source',
            type=str,
            default='all',
            choices=['all', 'collaborative', 'similarity'],
            help='Which data to rebuild (default: all)',
        )
        parser.add_argument(
            '--clear-cache',
            action='store_true',
            help='Clear product cache before building',
        )

    def handle(self, *args, **options):
        source = options['source']

        if options['clear_cache']:
            clear_product_cache()
            self.stdout.write('Product cache cleared.')

        if source in ('all', 'collaborative'):
            self.stdout.write('Building co-occurrence matrix...')
            co_count = build_co_occurrence_matrix()
            self.stdout.write(
                self.style.SUCCESS(f'  → {co_count} co-occurrence pairs created.')
            )

        if source in ('all', 'similarity'):
            self.stdout.write('Building similarity matrix...')
            sim_count = build_similarity_matrix()
            self.stdout.write(
                self.style.SUCCESS(f'  → {sim_count} similarity pairs created.')
            )

        self.stdout.write(self.style.SUCCESS('Recommendation data build complete.'))
