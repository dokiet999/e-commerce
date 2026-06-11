import os

from django.conf import settings
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Train RNN/LSTM/BiLSTM models for next-product prediction'

    def add_arguments(self, parser):
        parser.add_argument(
            '--csv-path',
            default=os.path.join(settings.BASE_DIR, 'data_user500.csv'),
            help='Path to data_user500.csv',
        )
        parser.add_argument(
            '--models',
            default='rnn,lstm,bilstm',
            help='Comma-separated model types: rnn,lstm,bilstm',
        )
        parser.add_argument(
            '--preferred',
            default='lstm',
            choices=['rnn', 'lstm', 'bilstm'],
            help='Model copied to next_product_preferred.pt',
        )
        parser.add_argument('--epochs', type=int, default=30)
        parser.add_argument('--batch-size', type=int, default=32)
        parser.add_argument('--lr', type=float, default=0.001)
        parser.add_argument('--max-seq-len', type=int, default=20)

    def handle(self, *args, **options):
        from ml.train_next_product import train_next_product_models

        self.stdout.write('Training next-product models...')
        summary = train_next_product_models(
            csv_path=options['csv_path'],
            model_dir=settings.ML_MODEL_DIR,
            model_types=options['models'],
            preferred=options['preferred'],
            epochs=options['epochs'],
            batch_size=options['batch_size'],
            lr=options['lr'],
            max_seq_len=options['max_seq_len'],
        )

        self.stdout.write(
            f"Samples: {summary['num_samples']} "
            f"(train={summary['num_train']}, val={summary['num_val']}, "
            f"test={summary['num_test']})"
        )
        self.stdout.write(f"Device: {summary['device']}")
        self.stdout.write('')

        for model_type, metrics in summary['results'].items():
            self.stdout.write(
                f"{model_type.upper():6} "
                f"val_loss={metrics['val_loss']:.4f} "
                f"test_loss={metrics['test_loss']:.4f} "
                f"acc@1={metrics['accuracy_at_1']:.2%} "
                f"hit@5={metrics['accuracy_at_5']:.2%} "
                f"mrr@5={metrics['mrr_at_5']:.4f}"
            )

        self.stdout.write('')
        self.stdout.write(f"Best by HitRate@5: {summary['best_model'].upper()}")
        self.stdout.write(f"Preferred for API: {summary['preferred'].upper()}")
        self.stdout.write(
            'LSTM is preferred because it captures behavior sequences well while '
            'remaining lighter than BiLSTM for realtime inference.'
        )
        self.stdout.write(
            self.style.SUCCESS(f"Saved artifacts to {summary['model_dir']}")
        )
