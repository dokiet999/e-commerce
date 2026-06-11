"""Train and compare RNN/LSTM/BiLSTM models for next-product prediction."""

import os
import shutil
from copy import deepcopy

import numpy as np
import torch
import torch.nn as nn

from .model_next_product import NextProductModel
from .next_product_pipeline import (
    DEFAULT_MAX_SEQ_LEN,
    make_loader,
    prepare_next_product_data,
    vocab_sizes,
)

MODEL_TYPES = ('rnn', 'lstm', 'bilstm')


def train_next_product_models(
    csv_path,
    model_dir,
    model_types=None,
    preferred='lstm',
    epochs=30,
    batch_size=32,
    lr=0.001,
    max_seq_len=DEFAULT_MAX_SEQ_LEN,
):
    model_types = _normalize_model_types(model_types)
    if preferred not in MODEL_TYPES:
        raise ValueError("preferred must be one of: rnn, lstm, bilstm")
    if preferred not in model_types:
        model_types.append(preferred)

    os.makedirs(model_dir, exist_ok=True)
    data = prepare_next_product_data(csv_path, max_seq_len=max_seq_len)
    if not data['samples']:
        raise ValueError('No training samples found. Need at least 2 events per user.')

    train_loader = make_loader(data['train_samples'], batch_size, shuffle=True)
    val_loader = make_loader(data['val_samples'], batch_size, shuffle=False)
    test_loader = make_loader(data['test_samples'], batch_size, shuffle=False)

    sizes = vocab_sizes(data['vocabs'])
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

    results = {}
    histories = {}
    for model_type in model_types:
        model, history, metrics, best_state = _train_one_model(
            model_type=model_type,
            sizes=sizes,
            train_loader=train_loader,
            val_loader=val_loader,
            test_loader=test_loader,
            device=device,
            epochs=epochs,
            lr=lr,
        )
        histories[model_type] = history
        results[model_type] = metrics

        checkpoint = _checkpoint(
            model=model,
            best_state=best_state,
            model_type=model_type,
            vocabs=data['vocabs'],
            sizes=sizes,
            max_seq_len=max_seq_len,
            metrics=metrics,
            history=history,
        )
        torch.save(
            checkpoint,
            os.path.join(model_dir, f'next_product_{model_type}.pt'),
        )

    best_type = max(
        results,
        key=lambda name: (results[name]['accuracy_at_5'], results[name]['accuracy_at_1']),
    )
    shutil.copyfile(
        os.path.join(model_dir, f'next_product_{best_type}.pt'),
        os.path.join(model_dir, 'next_product_best.pt'),
    )
    shutil.copyfile(
        os.path.join(model_dir, f'next_product_{preferred}.pt'),
        os.path.join(model_dir, 'next_product_preferred.pt'),
    )

    _save_plots(histories, results, model_dir)

    return {
        'model_types': model_types,
        'preferred': preferred,
        'best_model': best_type,
        'results': results,
        'histories': histories,
        'num_samples': len(data['samples']),
        'num_train': len(data['train_samples']),
        'num_val': len(data['val_samples']),
        'num_test': len(data['test_samples']),
        'device': str(device),
        'model_dir': model_dir,
    }


def _train_one_model(
    model_type,
    sizes,
    train_loader,
    val_loader,
    test_loader,
    device,
    epochs,
    lr,
):
    model = NextProductModel(
        num_products=sizes['num_products'],
        num_actions=sizes['num_actions'],
        num_categories=sizes['num_categories'],
        num_devices=sizes['num_devices'],
        num_output_products=sizes['num_output_products'],
        model_type=model_type,
    ).to(device)

    criterion = nn.CrossEntropyLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)

    history = {'train_loss': [], 'val_loss': []}
    best_state = None
    best_val_loss = float('inf')

    for _ in range(epochs):
        model.train()
        train_losses = []
        for batch in train_loader:
            product_ids, actions, categories, devices, seq_lengths, labels = [
                item.to(device) for item in batch
            ]

            optimizer.zero_grad()
            logits = model(product_ids, actions, categories, devices, seq_lengths)
            loss = criterion(logits, labels)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            train_losses.append(float(loss.item()))

        val_metrics = evaluate_model(model, val_loader, device, criterion)
        avg_train = float(np.mean(train_losses)) if train_losses else 0.0
        history['train_loss'].append(avg_train)
        history['val_loss'].append(val_metrics['loss'])

        if val_metrics['loss'] < best_val_loss:
            best_val_loss = val_metrics['loss']
            best_state = deepcopy(model.state_dict())

    if best_state is not None:
        model.load_state_dict(best_state)

    val_metrics = evaluate_model(model, val_loader, device, criterion)
    test_metrics = evaluate_model(model, test_loader, device, criterion)
    metrics = {
        'val_loss': val_metrics['loss'],
        'test_loss': test_metrics['loss'],
        'accuracy_at_1': test_metrics['accuracy_at_1'],
        'accuracy_at_5': test_metrics['accuracy_at_5'],
        'mrr_at_5': test_metrics['mrr_at_5'],
    }
    return model, history, metrics, best_state


def evaluate_model(model, loader, device, criterion=None):
    if criterion is None:
        criterion = nn.CrossEntropyLoss()

    model.eval()
    losses = []
    total = 0
    correct_at_1 = 0
    correct_at_5 = 0
    reciprocal_ranks = []

    with torch.no_grad():
        for batch in loader:
            product_ids, actions, categories, devices, seq_lengths, labels = [
                item.to(device) for item in batch
            ]
            logits = model(product_ids, actions, categories, devices, seq_lengths)
            loss = criterion(logits, labels)
            losses.append(float(loss.item()))

            k = min(5, logits.size(1))
            topk = torch.topk(logits, k=k, dim=1).indices
            total += labels.size(0)
            correct_at_1 += (topk[:, 0] == labels).sum().item()
            correct_at_5 += (topk == labels.unsqueeze(1)).any(dim=1).sum().item()

            for row, label in zip(topk, labels):
                matches = (row == label).nonzero(as_tuple=False)
                if matches.numel():
                    reciprocal_ranks.append(1.0 / float(matches[0].item() + 1))
                else:
                    reciprocal_ranks.append(0.0)

    return {
        'loss': float(np.mean(losses)) if losses else 0.0,
        'accuracy_at_1': correct_at_1 / max(total, 1),
        'accuracy_at_5': correct_at_5 / max(total, 1),
        'mrr_at_5': float(np.mean(reciprocal_ranks)) if reciprocal_ranks else 0.0,
    }


def _checkpoint(
    model,
    best_state,
    model_type,
    vocabs,
    sizes,
    max_seq_len,
    metrics,
    history,
):
    return {
        'model_state_dict': best_state or model.state_dict(),
        'model_type': model_type,
        'vocabs': vocabs,
        'sizes': sizes,
        'max_seq_len': max_seq_len,
        'metrics': metrics,
        'history': history,
        'model_config': {
            'hidden_size': model.hidden_size,
            'num_layers': model.num_layers,
        },
    }


def _normalize_model_types(model_types):
    if model_types is None:
        return list(MODEL_TYPES)
    if isinstance(model_types, str):
        model_types = [
            item.strip().lower() for item in model_types.split(',') if item.strip()
        ]
    normalized = []
    for model_type in model_types:
        if model_type not in MODEL_TYPES:
            raise ValueError(f'Unknown model type: {model_type}')
        if model_type not in normalized:
            normalized.append(model_type)
    return normalized or list(MODEL_TYPES)


def _save_plots(histories, results, model_dir):
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
    except ImportError:
        return

    fig, axes = plt.subplots(1, 2, figsize=(13, 5))
    for model_type, history in histories.items():
        epochs = range(1, len(history['train_loss']) + 1)
        axes[0].plot(epochs, history['train_loss'], label=f'{model_type.upper()} train')
        axes[0].plot(
            epochs,
            history['val_loss'],
            linestyle='--',
            label=f'{model_type.upper()} val',
        )
    axes[0].set_title('Next-product loss')
    axes[0].set_xlabel('Epoch')
    axes[0].set_ylabel('Loss')
    axes[0].legend()
    axes[0].grid(alpha=0.3)

    names = list(results.keys())
    x = np.arange(len(names))
    width = 0.35
    axes[1].bar(
        x - width / 2,
        [results[name]['accuracy_at_1'] for name in names],
        width,
        label='Accuracy@1',
    )
    axes[1].bar(
        x + width / 2,
        [results[name]['accuracy_at_5'] for name in names],
        width,
        label='HitRate@5',
    )
    axes[1].set_title('Next-product ranking metrics')
    axes[1].set_xticks(x)
    axes[1].set_xticklabels([name.upper() for name in names])
    axes[1].set_ylim(0, 1)
    axes[1].legend()
    axes[1].grid(axis='y', alpha=0.3)

    plt.tight_layout()
    plt.savefig(
        os.path.join(model_dir, 'next_product_comparison.png'),
        dpi=150,
        bbox_inches='tight',
    )
    plt.close(fig)
