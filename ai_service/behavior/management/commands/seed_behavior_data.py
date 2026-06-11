import logging
from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Generate synthetic behavior data for training'

    def add_arguments(self, parser):
        parser.add_argument('--users', type=int, default=30)
        parser.add_argument('--events-per-user', type=int, default=25)

    def handle(self, *args, **options):
        from seed_behavior_data import seed

        count = seed(
            num_users=options['users'],
            events_per_user=options['events_per_user'],
        )
        self.stdout.write(self.style.SUCCESS(f"Created {count} behavior events"))
