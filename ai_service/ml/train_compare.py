"""
Train and compare RNN / LSTM / BiLSTM models.
Generates loss curves, accuracy chart, confusion matrix.

Usage (inside Docker):
    docker exec -w /app/ai_service ai-service python ml/train_compare.py

Output:
    ml/saved_models/plot_loss_curves.png
    ml/saved_models/plot_accuracy.png
    ml/saved_models/plot_confusion_bilstm.png
"""

import os
import sys
import logging

import numpy as np
import torch
import torch.nn as nn
from torch.utils.data import DataLoader, TensorDataset
from sklearn.model_selection import train_test_split
from sklearn.metrics import confusion_matrix, f1_score, classification_report

import django
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ai_config.settings')
django.setup()

from ml.model_behavior import BehaviorModel, BehaviorModelLoss
from ml.train import prepare_dataset_from_db

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

EPOCHS = 30
BATCH_SIZE = 16
LR = 0.001
MODEL_DIR = os.path.join(os.path.dirname(__file__), 'saved_models')
os.makedirs(MODEL_DIR, exist_ok=True)

INTENT_NAMES = ['browsing', 'buying', 'comparing', 'returning']


def make_loaders(data, batch_size):
    n = len(data['intent_labels'])
    if n < 4:
        train_idx = val_idx = list(range(n))
    else:
        train_idx, val_idx = train_test_split(
            range(n), test_size=0.2, random_state=42,
        )

    def loader(indices, shuffle=True):
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
            shuffle=shuffle,
        )

    return loader(train_idx, shuffle=True), loader(val_idx, shuffle=False), val_idx


def train_one_model(model_type, data, device):
    train_loader, val_loader, val_idx = make_loaders(data, BATCH_SIZE)

    model = BehaviorModel(
        num_event_types=7, num_categories=10,
        num_intents=4, num_output_categories=10,
        model_type=model_type,
    ).to(device)

    criterion = BehaviorModelLoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=LR)
    scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
        optimizer, mode='min', patience=5, factor=0.5,
    )

    history = {'train_loss': [], 'val_loss': [], 'val_acc': []}
    best_val_loss = float('inf')
    best_state = None

    bar_width = 30
    for epoch in range(EPOCHS):
        # Train
        model.train()
        train_losses = []
        for batch in train_loader:
            evt, cat, num, seq_len, glob, y_intent, y_cat, y_purch = [
                b.to(device) for b in batch
            ]
            optimizer.zero_grad()
            logits, cat_prefs, purch, _ = model(evt, cat, num, seq_len, glob)
            loss, d = criterion(logits, cat_prefs, purch, y_intent, y_cat, y_purch)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            train_losses.append(d['total_loss'])

        # Validate
        model.eval()
        val_losses, correct, total = [], 0, 0
        with torch.no_grad():
            for batch in val_loader:
                evt, cat, num, seq_len, glob, y_intent, y_cat, y_purch = [
                    b.to(device) for b in batch
                ]
                logits, cat_prefs, purch, _ = model(evt, cat, num, seq_len, glob)
                _, d = criterion(logits, cat_prefs, purch, y_intent, y_cat, y_purch)
                val_losses.append(d['total_loss'])
                preds = logits.argmax(dim=1)
                correct += (preds == y_intent).sum().item()
                total += y_intent.size(0)

        avg_train = float(np.mean(train_losses))
        avg_val = float(np.mean(val_losses))
        acc = correct / max(total, 1)
        scheduler.step(avg_val)

        history['train_loss'].append(avg_train)
        history['val_loss'].append(avg_val)
        history['val_acc'].append(acc)

        if avg_val < best_val_loss:
            best_val_loss = avg_val
            best_state = {k: v.cpu().clone() for k, v in model.state_dict().items()}

        # Progress bar
        filled = int((epoch + 1) / EPOCHS * bar_width)
        bar = '█' * filled + '░' * (bar_width - filled)
        print(
            f'\r  [{bar}] {epoch+1:2d}/{EPOCHS} '
            f'| train={avg_train:.4f} val={avg_val:.4f} acc={acc:.2%}',
            end='', flush=True,
        )

    print()  # newline after progress bar

    # Restore best weights
    model.load_state_dict(best_state)
    torch.save(
        {'model_state_dict': best_state, 'model_type': model_type},
        os.path.join(MODEL_DIR, f'model_{model_type}_best.pt'),
    )
    if model_type == 'bilstm':
        torch.save(
            {'model_state_dict': best_state, 'model_type': model_type},
            os.path.join(MODEL_DIR, 'model_best.pt'),
        )

    # Collect val predictions for metrics
    model.eval()
    all_preds, all_true = [], []
    _, val_loader_noshuffle, _ = make_loaders(data, BATCH_SIZE)
    with torch.no_grad():
        for batch in val_loader_noshuffle:
            evt, cat, num, seq_len, glob, y_intent, y_cat, y_purch = [
                b.to(device) for b in batch
            ]
            logits, _, _, _ = model(evt, cat, num, seq_len, glob)
            all_preds.extend(logits.argmax(dim=1).cpu().numpy())
            all_true.extend(y_intent.cpu().numpy())

    best_acc = max(history['val_acc'])
    best_val = min(history['val_loss'])
    f1 = f1_score(all_true, all_preds, average='macro', zero_division=0)

    return history, best_acc, best_val, f1, model, all_preds, all_true


def print_separator(char='─', width=65):
    print(char * width)


def print_comparison_table(results):
    print_separator('═')
    print('  SO SÁNH 3 MÔ HÌNH (500 users, 30 epochs)')
    print_separator('═')
    header = f"  {'Chỉ số':<28} {'RNN':>10} {'LSTM':>10} {'BiLSTM':>10}"
    print(header)
    print_separator()

    metrics = [
        ('Best Val Loss ↓',        'best_val',  '{:.4f}'),
        ('Best Intent Accuracy ↑', 'best_acc',  '{:.2%}'),
        ('F1 Macro ↑',             'f1',        '{:.4f}'),
        ('Final Train Loss',       'final_train','{:.4f}'),
        ('Best Epoch',             'best_epoch', '{:>10}'),
    ]
    for label, key, fmt in metrics:
        row = f"  {label:<28}"
        for mt in ['rnn', 'lstm', 'bilstm']:
            val = results[mt][key]
            row += f" {fmt.format(val):>10}"
        print(row)

    print_separator('═')
    winner = min(results, key=lambda m: results[m]['best_val'])
    print(f'  → Mô hình tốt nhất (val_loss): {winner.upper()}')
    print_separator('═')


def generate_plots(histories, results):
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        from sklearn.metrics import ConfusionMatrixDisplay
    except ImportError:
        print('  [!] matplotlib not installed — skip plots')
        return

    colors = {'rnn': '#e74c3c', 'lstm': '#f39c12', 'bilstm': '#2ecc71'}
    epochs_x = range(1, EPOCHS + 1)

    # ── Plot 1: Loss curves ──────────────────────────────────────
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    fig.suptitle('Loss Curves: RNN / LSTM / BiLSTM (30 epochs)', fontsize=14, fontweight='bold')

    for mt, hist in histories.items():
        axes[0].plot(epochs_x, hist['train_loss'], color=colors[mt],
                     label=mt.upper(), linewidth=2)
        axes[1].plot(epochs_x, hist['val_loss'], color=colors[mt],
                     label=mt.upper(), linewidth=2,
                     linestyle='--' if mt != 'bilstm' else '-')

    for ax, title in zip(axes, ['Train Loss', 'Validation Loss']):
        ax.set_xlabel('Epoch')
        ax.set_ylabel('Loss')
        ax.set_title(title)
        ax.legend()
        ax.grid(alpha=0.3)

    plt.tight_layout()
    p1 = os.path.join(MODEL_DIR, 'plot_loss_curves.png')
    plt.savefig(p1, dpi=150, bbox_inches='tight')
    plt.close()
    print(f'  Saved: {p1}')

    # ── Plot 2: Accuracy & F1 bar chart ─────────────────────────
    fig, ax = plt.subplots(figsize=(9, 5))
    models = ['RNN', 'LSTM', 'BiLSTM']
    keys = ['rnn', 'lstm', 'bilstm']
    accs = [results[k]['best_acc'] * 100 for k in keys]
    f1s  = [results[k]['f1'] * 100 for k in keys]

    x = np.arange(len(models))
    w = 0.35
    bars1 = ax.bar(x - w/2, accs, w, label='Intent Accuracy (%)',
                   color=[colors[k] for k in keys], alpha=0.85)
    bars2 = ax.bar(x + w/2, f1s,  w, label='F1 Macro (%)',
                   color=[colors[k] for k in keys], alpha=0.45, hatch='//')

    for bar in list(bars1) + list(bars2):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.5,
                f'{bar.get_height():.1f}%', ha='center', va='bottom', fontsize=9)

    ax.set_xticks(x)
    ax.set_xticklabels(models, fontsize=12)
    ax.set_ylabel('%')
    ax.set_ylim(0, 115)
    ax.set_title('So sánh Intent Accuracy và F1 Macro của 3 mô hình', fontweight='bold')
    ax.legend()
    ax.grid(axis='y', alpha=0.3)
    plt.tight_layout()
    p2 = os.path.join(MODEL_DIR, 'plot_accuracy.png')
    plt.savefig(p2, dpi=150, bbox_inches='tight')
    plt.close()
    print(f'  Saved: {p2}')

    # ── Plot 3: Confusion matrix BiLSTM ──────────────────────────
    preds = results['bilstm']['preds']
    true  = results['bilstm']['true']
    cm    = confusion_matrix(true, preds, labels=[0, 1, 2, 3])

    fig, ax = plt.subplots(figsize=(7, 6))
    disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=INTENT_NAMES)
    disp.plot(ax=ax, colorbar=True, cmap='Blues')
    ax.set_title('Confusion Matrix — BiLSTM (Validation Set)', fontweight='bold')
    plt.tight_layout()
    p3 = os.path.join(MODEL_DIR, 'plot_confusion_bilstm.png')
    plt.savefig(p3, dpi=150, bbox_inches='tight')
    plt.close()
    print(f'  Saved: {p3}')

    return p1, p2, p3


def main():
    print_separator('═')
    print('  TRAINING PIPELINE: RNN / LSTM / BiLSTM')
    print('  Dataset: 500 users | Epochs: 30 | Batch: 16 | LR: 0.001')
    print_separator('═')

    logger.info('Loading dataset from DB...')
    data = prepare_dataset_from_db()
    if data is None:
        print('ERROR: No data. Run seed_behavior_data.py first.')
        sys.exit(1)

    print(f'  Dataset: {len(data["intent_labels"])} users/sessions')
    print(f'  Train: {int(len(data["intent_labels"])*0.8)} | Val: {int(len(data["intent_labels"])*0.2)}')

    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f'  Device: {device}')
    print_separator()

    histories = {}
    results = {}

    for model_type in ['rnn', 'lstm', 'bilstm']:
        print(f'\n  Training {model_type.upper()}...')
        hist, best_acc, best_val, f1, model, preds, true = train_one_model(
            model_type, data, device,
        )
        histories[model_type] = hist
        best_epoch = int(np.argmin(hist['val_loss'])) + 1
        results[model_type] = {
            'best_acc': best_acc,
            'best_val': best_val,
            'f1': f1,
            'final_train': hist['train_loss'][-1],
            'best_epoch': best_epoch,
            'preds': preds,
            'true': true,
        }
        print(f'  → Best val_loss={best_val:.4f} | best_acc={best_acc:.2%} | F1={f1:.4f} | best_epoch={best_epoch}')

        # Classification report
        print('\n  Classification Report:')
        report = classification_report(
            true, preds,
            target_names=INTENT_NAMES,
            zero_division=0,
        )
        for line in report.split('\n'):
            print(f'    {line}')

    print()
    print_comparison_table(results)

    print('\n  Generating plots...')
    generate_plots(histories, results)

    print('\n  Done! Model files saved to:', MODEL_DIR)


if __name__ == '__main__':
    main()
