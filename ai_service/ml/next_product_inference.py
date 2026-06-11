"""Inference helpers for the preferred next-product model."""

import os

import torch

from .model_next_product import NextProductModel
from .next_product_pipeline import encode_events_for_inference

_model = None
_checkpoint = None
_device = None


class NextProductModelNotFound(RuntimeError):
    pass


def get_default_model_path():
    try:
        from django.conf import settings
        return os.path.join(settings.ML_MODEL_DIR, 'next_product_preferred.pt')
    except Exception:
        return os.path.join(
            os.path.dirname(__file__),
            'saved_models',
            'next_product_preferred.pt',
        )


def load_next_product_model(model_path=None):
    global _model, _checkpoint, _device

    model_path = model_path or get_default_model_path()
    if not os.path.exists(model_path):
        raise NextProductModelNotFound(
            f'Next-product model not found at {model_path}. '
            'Run: python manage.py train_next_product --models rnn,lstm,bilstm '
            '--preferred lstm'
        )

    _device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    _checkpoint = torch.load(model_path, map_location=_device, weights_only=False)
    sizes = _checkpoint['sizes']

    _model = NextProductModel(
        num_products=sizes['num_products'],
        num_actions=sizes['num_actions'],
        num_categories=sizes['num_categories'],
        num_devices=sizes['num_devices'],
        num_output_products=sizes['num_output_products'],
        model_type=_checkpoint.get('model_type', 'lstm'),
    ).to(_device)
    _model.load_state_dict(_checkpoint['model_state_dict'])
    _model.eval()
    return _model


def get_next_product_model():
    global _model
    if _model is None:
        load_next_product_model()
    return _model


def predict_next_products(events, top_k=5):
    if not events:
        raise ValueError('events is required')

    model = get_next_product_model()
    vocabs = _checkpoint['vocabs']
    max_seq_len = _checkpoint['max_seq_len']
    model_type = _checkpoint.get('model_type', 'lstm')

    encoded = encode_events_for_inference(events, vocabs, max_seq_len)
    if encoded['seq_length'] == 0:
        raise ValueError('events must contain at least one valid item')

    top_k = max(1, min(int(top_k), 20))

    with torch.no_grad():
        product_ids = torch.LongTensor(encoded['product_ids']).unsqueeze(0).to(_device)
        actions = torch.LongTensor(encoded['actions']).unsqueeze(0).to(_device)
        categories = torch.LongTensor(encoded['categories']).unsqueeze(0).to(_device)
        devices = torch.LongTensor(encoded['devices']).unsqueeze(0).to(_device)
        seq_lengths = torch.LongTensor([encoded['seq_length']]).to(_device)

        logits = model(product_ids, actions, categories, devices, seq_lengths)
        probs = torch.softmax(logits, dim=1).squeeze(0)
        k = min(top_k, probs.size(0))
        scores, indices = torch.topk(probs, k=k)

    label_to_product = vocabs['label_to_product']
    predictions = []
    for rank, (score, idx) in enumerate(zip(scores.cpu(), indices.cpu()), start=1):
        label_idx = int(idx.item())
        product_id = label_to_product.get(label_idx) or label_to_product.get(str(label_idx))
        predictions.append({
            'product_id': product_id,
            'score': float(score.item()),
            'rank': rank,
        })

    return {
        'recommendation_type': f'next_product_{model_type}',
        'model_type': model_type,
        'count': len(predictions),
        'predictions': predictions,
    }
