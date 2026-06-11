"""
Inference service — loads trained model and predicts behavior.
Singleton pattern: model loaded once at import time.
"""

import os
import logging

import torch
import numpy as np

from .model_behavior import BehaviorModel
from .data_pipeline import events_to_features

logger = logging.getLogger(__name__)

# Intent labels
INTENT_LABELS = ['browsing', 'buying', 'comparing', 'returning']

# Singleton model instance
_model = None
_device = None


def _get_model_path():
    try:
        from django.conf import settings
        return os.path.join(settings.ML_MODEL_DIR, 'model_behavior.pth')
    except Exception:
        return os.path.join(
            os.path.dirname(__file__), 'saved_models', 'model_behavior.pth'
        )


def load_model():
    """Load the trained model. Called once."""
    global _model, _device

    model_path = _get_model_path()
    _device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

    _model = BehaviorModel(
        num_event_types=7,
        num_categories=10,
        num_intents=4,
        num_output_categories=10,
    ).to(_device)

    if os.path.exists(model_path):
        checkpoint = torch.load(model_path, map_location=_device, weights_only=True)
        _model.load_state_dict(checkpoint['model_state_dict'])
        logger.info(
            f"Loaded model from {model_path} "
            f"(epoch={checkpoint.get('epoch')}, "
            f"accuracy={checkpoint.get('accuracy', 'N/A')})"
        )
    else:
        logger.warning(
            f"No trained model found at {model_path}. "
            "Using randomly initialized model. Run 'python manage.py train_model' first."
        )

    _model.eval()
    return _model


def get_model():
    """Get the singleton model instance."""
    global _model
    if _model is None:
        load_model()
    return _model


def predict_behavior(events):
    """
    Predict customer behavior from a list of event dicts.

    Args:
        events: list of dicts with event_type, product_id, category_id, metadata, created_at

    Returns:
        dict with:
            predicted_intent: str
            intent_probabilities: dict
            category_preferences: dict (category_id -> score)
            purchase_likelihood: float
            attention_weights: list (which events were most important)
    """
    model = get_model()
    features = events_to_features(events)

    with torch.no_grad():
        event_types = torch.LongTensor(features['event_types']).unsqueeze(0).to(_device)
        categories = torch.LongTensor(features['categories']).unsqueeze(0).to(_device)
        numerical = torch.FloatTensor(features['numerical_features']).unsqueeze(0).to(_device)
        seq_len = torch.LongTensor([features['seq_length']]).to(_device)
        global_feat = torch.FloatTensor(features['global_features']).unsqueeze(0).to(_device)

        intent_logits, cat_prefs, purchase_prob, attn_weights = model(
            event_types, categories, numerical, seq_len, global_feat,
        )

        # Process outputs
        intent_probs = torch.softmax(intent_logits, dim=-1).squeeze(0).cpu().numpy()
        predicted_intent_idx = int(intent_probs.argmax())

        cat_scores = torch.softmax(cat_prefs, dim=-1).squeeze(0).cpu().numpy()
        purchase = float(purchase_prob.squeeze().cpu().numpy())

        attn = attn_weights.squeeze(0).cpu().numpy()
        actual_len = features['seq_length']
        attn_list = attn[:actual_len].tolist() if actual_len > 0 else []

    return {
        'predicted_intent': INTENT_LABELS[predicted_intent_idx],
        'intent_probabilities': {
            label: float(prob)
            for label, prob in zip(INTENT_LABELS, intent_probs)
        },
        'category_preferences': {
            str(i): float(score)
            for i, score in enumerate(cat_scores)
            if score > 0.05
        },
        'purchase_likelihood': purchase,
        'attention_weights': attn_list,
    }
