import logging
from django.core.management.base import BaseCommand

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Train the behavior prediction model'

    def add_arguments(self, parser):
        parser.add_argument('--epochs', type=int, default=30)
        parser.add_argument('--batch-size', type=int, default=16)
        parser.add_argument('--lr', type=float, default=0.001)
        parser.add_argument(
            '--model-type', type=str, default='bilstm',
            choices=['rnn', 'lstm', 'bilstm'],
            help='Model architecture: rnn, lstm, or bilstm (default: bilstm)',
        )

    def handle(self, *args, **options):
        logging.basicConfig(level=logging.INFO)
        from ml.train import train_model

        model_type = options['model_type']
        self.stdout.write(f"Starting model training ({model_type.upper()})...")
        model = train_model(
            epochs=options['epochs'],
            batch_size=options['batch_size'],
            lr=options['lr'],
            model_type=model_type,
        )
        if model:
            self.stdout.write(self.style.SUCCESS("Model training completed."))
        else:
            self.stdout.write(self.style.WARNING("No training data available."))
