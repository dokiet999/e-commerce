"""
Training pipeline for the BehaviorModel.

Usage (as Django management command):
    python manage.py train_model
    python manage.py train_model --epochs 50 --batch-size 32
"""

import os
import logging

import numpy as np
import torch
from torch.utils.data import DataLoader, TensorDataset
from sklearn.model_selection import train_test_split

from .model_behavior import BehaviorModel, BehaviorModelLoss
from .data_pipeline import events_to_features, assign_intent_label, MAX_SEQ_LEN

logger = logging.getLogger(__name__)


def prepare_dataset_from_db():
    """Load events from DB and prepare training tensors."""
    import django
    django.setup()
    from behavior.models import BehaviorEvent

    # Group events by user_id or session_id
    user_groups = {}
    for event in BehaviorEvent.objects.all().order_by('created_at').values(
        'user_id', 'session_id', 'event_type', 'product_id',
        'category_id', 'metadata', 'created_at',
    ):
        key = event['user_id'] or event['session_id']
        if key not in user_groups:
            user_groups[key] = []
        user_groups[key].append(event)

    if not user_groups:
        logger.warning("No behavior data found. Run seed_behavior_data first.")
        return None

    all_event_types = []
    all_categories = []
    all_numerical = []
    all_seq_lengths = []
    all_global = []
    all_intent_labels = []
    all_category_labels = []
    all_purchase_labels = []

    for key, events in user_groups.items():
        features = events_to_features(events)

        all_event_types.append(features['event_types'])
        all_categories.append(features['categories'])
        all_numerical.append(features['numerical_features'])
        all_seq_lengths.append(features['seq_length'])
        all_global.append(features['global_features'])

        # Labels
        intent = assign_intent_label(events)
        all_intent_labels.append(intent)

        # Category label = most viewed category
        cat_counts = {}
        for e in events:
            c = e.get('category_id')
            if c:
                cat_counts[c] = cat_counts.get(c, 0) + 1
        top_cat = max(cat_counts, key=cat_counts.get) if cat_counts else 0
        all_category_labels.append(min(top_cat, 9))

        # Purchase label = has checkout or high cart rate
        has_checkout = any(e['event_type'] == 'checkout' for e in events)
        cart_count = sum(1 for e in events if e['event_type'] == 'add_to_cart')
        all_purchase_labels.append(1.0 if has_checkout or cart_count >= 3 else 0.0)

    return {
        'event_types': np.array(all_event_types),
        'categories': np.array(all_categories),
        'numerical': np.array(all_numerical),
        'seq_lengths': np.array(all_seq_lengths),
        'global_features': np.array(all_global),
        'intent_labels': np.array(all_intent_labels),
        'category_labels': np.array(all_category_labels),
        'purchase_labels': np.array(all_purchase_labels, dtype=np.float32),
    }


def train_model(epochs=30, batch_size=16, lr=0.001, model_dir=None, model_type='bilstm'):
    """Train the BehaviorModel and save checkpoint. model_type: 'rnn', 'lstm', 'bilstm'"""
    if model_dir is None:
        from django.conf import settings
        model_dir = settings.ML_MODEL_DIR

    os.makedirs(model_dir, exist_ok=True)

    logger.info("Preparing dataset...")
    data = prepare_dataset_from_db()
    if data is None:
        return None

    n_samples = len(data['intent_labels'])
    logger.info(f"Dataset size: {n_samples} users/sessions")

    if n_samples < 4:
        logger.warning("Not enough data for train/test split. Training on all data.")
        train_idx = list(range(n_samples))
        val_idx = train_idx
    else:
        train_idx, val_idx = train_test_split(
            range(n_samples), test_size=0.2, random_state=42,
        )

    def make_loader(indices):
        return DataLoader(
            TensorDataset(
                torch.LongTensor(data['event_types'][indices]),
                torch.LongTensor(data['categories'][indices]),
                torch.FloatTensor(data['numerical'][indices]),
                torch.LongTensor(data['seq_lengths'][indices]),
                torch.FloatTensor(data['global_features'][indices]),
                torch.LongTensor(data['intent_labels'][indices]),
                torch.LongTensor(data['category_labels'][indices]),
                torch.FloatTensor(data['purchase_labels'][indices]),
            ),
            batch_size=batch_size,
            shuffle=True,
        )

    train_loader = make_loader(train_idx)
    val_loader = make_loader(val_idx)

    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    logger.info(f"Training on: {device}")

    logger.info(f"Model type: {model_type}")
    model = BehaviorModel(
        num_event_types=7,
        num_categories=10,
        num_intents=4,
        num_output_categories=10,
        model_type=model_type,
    ).to(device)

    criterion = BehaviorModelLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode='min', patience=5, factor=0.5,
    )

    best_val_loss = float('inf')

    for epoch in range(epochs):
        # Train
        model.train()
        train_losses = []
        for batch in train_loader:
            (evt, cat, num, seq_len, glob, y_intent, y_cat, y_purch) = [
                b.to(device) for b in batch
            ]

            optimizer.zero_grad()
            intent_logits, cat_prefs, purch_prob, _ = model(
                evt, cat, num, seq_len, glob,
            )
            loss, loss_dict = criterion(
                intent_logits, cat_prefs, purch_prob,
                y_intent, y_cat, y_purch,
            )
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            train_losses.append(loss_dict['total_loss'])

        # Validate
        model.eval()
        val_losses = []
        correct_intent = 0
        total_val = 0
        with torch.no_grad():
            for batch in val_loader:
                (evt, cat, num, seq_len, glob, y_intent, y_cat, y_purch) = [
                    b.to(device) for b in batch
                ]
                intent_logits, cat_prefs, purch_prob, _ = model(
                    evt, cat, num, seq_len, glob,
                )
                _, loss_dict = criterion(
                    intent_logits, cat_prefs, purch_prob,
                    y_intent, y_cat, y_purch,
                )
                val_losses.append(loss_dict['total_loss'])
                preds = intent_logits.argmax(dim=1)
                correct_intent += (preds == y_intent).sum().item()
                total_val += y_intent.size(0)

        avg_train = np.mean(train_losses)
        avg_val = np.mean(val_losses)
        accuracy = correct_intent / max(total_val, 1)
        scheduler.step(avg_val)

        logger.info(
            f"Epoch {epoch+1}/{epochs} — "
            f"Train Loss: {avg_train:.4f}, Val Loss: {avg_val:.4f}, "
            f"Intent Acc: {accuracy:.4f}"
        )

        if avg_val < best_val_loss:
            best_val_loss = avg_val
            save_path = os.path.join(model_dir, f'model_{model_type}_best.pt')
            torch.save({
                'model_state_dict': model.state_dict(),
                'epoch': epoch,
                'val_loss': best_val_loss,
                'accuracy': accuracy,
                'model_type': model_type,
            }, save_path)
            # Also keep model_best.pt for bilstm (used by inference)
            if model_type == 'bilstm':
                torch.save({
                    'model_state_dict': model.state_dict(),
                    'epoch': epoch,
                    'val_loss': best_val_loss,
                    'accuracy': accuracy,
                    'model_type': model_type,
                }, os.path.join(model_dir, 'model_best.pt'))
            logger.info(f"  -> Saved best model (val_loss={best_val_loss:.4f}) -> {save_path}")

    logger.info(f"Training complete. Best val loss: {best_val_loss:.4f}")
    return model
