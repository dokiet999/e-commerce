"""Data preparation helpers for next-product prediction from CSV."""

import csv
import random
from collections import defaultdict
from datetime import datetime

import torch
from torch.utils.data import DataLoader, Dataset

PAD_TOKEN = '<PAD>'
UNK_TOKEN = '<UNK>'
DEFAULT_MAX_SEQ_LEN = 20


class NextProductDataset(Dataset):
    def __init__(self, samples):
        self.samples = samples

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        sample = self.samples[idx]
        return (
            torch.LongTensor(sample['product_ids']),
            torch.LongTensor(sample['actions']),
            torch.LongTensor(sample['categories']),
            torch.LongTensor(sample['devices']),
            torch.LongTensor([sample['seq_length']]).squeeze(0),
            torch.LongTensor([sample['label']]).squeeze(0),
        )


def load_csv_events(csv_path):
    """Load synthetic events from data_user500.csv."""
    events = []
    with open(csv_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            row['timestamp_obj'] = _parse_timestamp(row.get('timestamp'))
            events.append(row)
    return events


def build_vocabs(events):
    """Build categorical vocabularies.

    Input feature vocabularies reserve 0 for padding and 1 for unknown.
    Product labels use zero-based class ids for CrossEntropyLoss.
    """
    products = sorted({e['product_id'] for e in events if e.get('product_id')})
    actions = sorted({e['action'] for e in events if e.get('action')})
    categories = sorted({e['category'] for e in events if e.get('category')})
    devices = sorted({e['device'] for e in events if e.get('device')})

    product_to_label = {value: idx for idx, value in enumerate(products)}
    label_to_product = {idx: value for value, idx in product_to_label.items()}

    return {
        'product_to_label': product_to_label,
        'label_to_product': label_to_product,
        'product_to_input': _feature_vocab(products),
        'action_to_idx': _feature_vocab(actions),
        'category_to_idx': _feature_vocab(categories),
        'device_to_idx': _feature_vocab(devices),
    }


def create_samples(events, vocabs, max_seq_len=DEFAULT_MAX_SEQ_LEN):
    """Create sliding-window samples. The next product is the label."""
    grouped = defaultdict(list)
    for event in events:
        grouped[event['user_id']].append(event)

    samples = []
    for user_events in grouped.values():
        user_events = sorted(user_events, key=lambda e: e['timestamp_obj'])
        if len(user_events) < 2:
            continue

        for target_idx in range(1, len(user_events)):
            history = user_events[max(0, target_idx - max_seq_len):target_idx]
            target = user_events[target_idx]
            if target.get('product_id') not in vocabs['product_to_label']:
                continue
            samples.append(_encode_sample(history, target, vocabs, max_seq_len))

    return samples


def split_samples(samples, train_ratio=0.8, val_ratio=0.1, seed=42):
    shuffled = list(samples)
    random.Random(seed).shuffle(shuffled)

    total = len(shuffled)
    train_end = int(total * train_ratio)
    val_end = train_end + int(total * val_ratio)

    train = shuffled[:train_end]
    val = shuffled[train_end:val_end]
    test = shuffled[val_end:]

    if not val and train:
        val = train[-1:]
    if not test and train:
        test = train[-1:]

    return train, val, test


def make_loader(samples, batch_size=32, shuffle=False):
    return DataLoader(
        NextProductDataset(samples),
        batch_size=batch_size,
        shuffle=shuffle,
    )


def prepare_next_product_data(csv_path, max_seq_len=DEFAULT_MAX_SEQ_LEN):
    events = load_csv_events(csv_path)
    vocabs = build_vocabs(events)
    samples = create_samples(events, vocabs, max_seq_len=max_seq_len)
    train, val, test = split_samples(samples)
    return {
        'events': events,
        'vocabs': vocabs,
        'samples': samples,
        'train_samples': train,
        'val_samples': val,
        'test_samples': test,
    }


def encode_events_for_inference(events, vocabs, max_seq_len):
    """Encode raw request events into one padded model input."""
    normalized = []
    for event in events:
        item = dict(event)
        item['timestamp_obj'] = _parse_timestamp(item.get('timestamp'))
        normalized.append(item)

    normalized = sorted(normalized, key=lambda e: e['timestamp_obj'])
    history = normalized[-max_seq_len:]
    seq_length = len(history)

    encoded = {
        'product_ids': [0] * max_seq_len,
        'actions': [0] * max_seq_len,
        'categories': [0] * max_seq_len,
        'devices': [0] * max_seq_len,
        'seq_length': seq_length,
    }

    for idx, event in enumerate(history):
        encoded['product_ids'][idx] = _lookup(
            vocabs['product_to_input'], event.get('product_id')
        )
        encoded['actions'][idx] = _lookup(
            vocabs['action_to_idx'], event.get('action')
        )
        encoded['categories'][idx] = _lookup(
            vocabs['category_to_idx'], event.get('category')
        )
        encoded['devices'][idx] = _lookup(
            vocabs['device_to_idx'], event.get('device')
        )

    return encoded


def vocab_sizes(vocabs):
    return {
        'num_products': len(vocabs['product_to_input']),
        'num_actions': len(vocabs['action_to_idx']),
        'num_categories': len(vocabs['category_to_idx']),
        'num_devices': len(vocabs['device_to_idx']),
        'num_output_products': len(vocabs['product_to_label']),
    }


def _feature_vocab(values):
    vocab = {PAD_TOKEN: 0, UNK_TOKEN: 1}
    for value in values:
        vocab[value] = len(vocab)
    return vocab


def _encode_sample(history, target, vocabs, max_seq_len):
    encoded = {
        'product_ids': [0] * max_seq_len,
        'actions': [0] * max_seq_len,
        'categories': [0] * max_seq_len,
        'devices': [0] * max_seq_len,
        'seq_length': len(history),
        'label': vocabs['product_to_label'][target['product_id']],
    }

    for idx, event in enumerate(history):
        encoded['product_ids'][idx] = _lookup(
            vocabs['product_to_input'], event.get('product_id')
        )
        encoded['actions'][idx] = _lookup(
            vocabs['action_to_idx'], event.get('action')
        )
        encoded['categories'][idx] = _lookup(
            vocabs['category_to_idx'], event.get('category')
        )
        encoded['devices'][idx] = _lookup(
            vocabs['device_to_idx'], event.get('device')
        )

    return encoded


def _lookup(vocab, value):
    return vocab.get(value, vocab[UNK_TOKEN])


def _parse_timestamp(value):
    if isinstance(value, datetime):
        return value
    if not value:
        return datetime.min
    for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S'):
        try:
            return datetime.strptime(str(value), fmt)
        except ValueError:
            continue
    return datetime.min
