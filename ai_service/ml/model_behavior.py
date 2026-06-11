"""
Deep Learning model for customer behavior analysis.

Architecture:
- Embedding layers for categorical features (event_type, category)
- LSTM layer to process action sequences (temporal patterns)
- Attention mechanism to weight important actions
- Multi-task output heads:
  1. Intent classification (browsing/buying/comparing/returning)
  2. Category preference distribution
  3. Purchase likelihood (scalar)
"""

import torch
import torch.nn as nn
import torch.nn.functional as F


class BehaviorAttention(nn.Module):
    """Attention layer to weight which actions in a sequence matter most."""

    def __init__(self, hidden_size):
        super().__init__()
        self.attention = nn.Sequential(
            nn.Linear(hidden_size, hidden_size // 2),
            nn.Tanh(),
            nn.Linear(hidden_size // 2, 1),
        )

    def forward(self, lstm_output, mask=None):
        # lstm_output: (batch, seq_len, hidden_size)
        scores = self.attention(lstm_output).squeeze(-1)  # (batch, seq_len)
        if mask is not None:
            scores = scores.masked_fill(~mask, float('-inf'))
        weights = F.softmax(scores, dim=-1)  # (batch, seq_len)
        context = torch.bmm(weights.unsqueeze(1), lstm_output).squeeze(1)
        return context, weights


class BehaviorModel(nn.Module):
    """
    Multi-task deep learning model for customer behavior prediction.

    Inputs:
        event_types: (batch, seq_len) - encoded event type IDs
        categories: (batch, seq_len) - encoded category IDs
        numerical_features: (batch, seq_len, num_numerical) - price, quantity, etc.
        seq_lengths: (batch,) - actual sequence lengths
        global_features: (batch, num_global) - aggregated user-level features

    Outputs:
        intent_logits: (batch, num_intents) - intent class probabilities
        category_prefs: (batch, num_categories) - category preference distribution
        purchase_prob: (batch, 1) - purchase likelihood
    """

    def __init__(
        self,
        num_event_types=7,
        num_categories=10,
        event_embed_dim=16,
        category_embed_dim=16,
        num_numerical=3,
        num_global_features=5,
        hidden_size=64,
        num_lstm_layers=2,
        num_intents=4,
        num_output_categories=10,
        dropout=0.3,
        model_type='bilstm',  # 'rnn', 'lstm', 'bilstm'
    ):
        super().__init__()
        self.model_type = model_type

        self.event_embedding = nn.Embedding(
            num_event_types + 1, event_embed_dim, padding_idx=0
        )
        self.category_embedding = nn.Embedding(
            num_categories + 1, category_embed_dim, padding_idx=0
        )

        lstm_input_size = event_embed_dim + category_embed_dim + num_numerical

        if model_type == 'rnn':
            self.rnn = nn.RNN(
                input_size=lstm_input_size,
                hidden_size=hidden_size,
                num_layers=num_lstm_layers,
                batch_first=True,
                dropout=dropout if num_lstm_layers > 1 else 0,
                bidirectional=False,
            )
            rnn_out_size = hidden_size
        elif model_type == 'lstm':
            self.rnn = nn.LSTM(
                input_size=lstm_input_size,
                hidden_size=hidden_size,
                num_layers=num_lstm_layers,
                batch_first=True,
                dropout=dropout if num_lstm_layers > 1 else 0,
                bidirectional=False,
            )
            rnn_out_size = hidden_size
        else:  # bilstm
            self.rnn = nn.LSTM(
                input_size=lstm_input_size,
                hidden_size=hidden_size,
                num_layers=num_lstm_layers,
                batch_first=True,
                dropout=dropout if num_lstm_layers > 1 else 0,
                bidirectional=True,
            )
            rnn_out_size = hidden_size * 2

        self.use_attention = (model_type in ('lstm', 'bilstm'))
        if self.use_attention:
            self.attention = BehaviorAttention(rnn_out_size)

        combined_size = rnn_out_size + num_global_features

        self.shared_fc = nn.Sequential(
            nn.Linear(combined_size, 128),
            nn.ReLU(),
            nn.Dropout(dropout),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Dropout(dropout),
        )

        # Task-specific heads
        self.intent_head = nn.Linear(64, num_intents)
        self.category_head = nn.Linear(64, num_output_categories)
        self.purchase_head = nn.Linear(64, 1)

    def forward(
        self, event_types, categories, numerical_features,
        seq_lengths, global_features,
    ):
        event_emb = self.event_embedding(event_types)
        cat_emb = self.category_embedding(categories)

        # Concatenate all sequence features
        seq_input = torch.cat([event_emb, cat_emb, numerical_features], dim=-1)

        # Pack sequences for RNN/LSTM
        packed = nn.utils.rnn.pack_padded_sequence(
            seq_input, seq_lengths.cpu().clamp(min=1),
            batch_first=True, enforce_sorted=False,
        )
        rnn_out, _ = self.rnn(packed)
        rnn_out, _ = nn.utils.rnn.pad_packed_sequence(
            rnn_out, batch_first=True,
        )

        # Attention (LSTM/BiLSTM) or last hidden state (RNN)
        max_len = rnn_out.size(1)
        if self.use_attention:
            mask = torch.arange(max_len, device=rnn_out.device).unsqueeze(0) < seq_lengths.unsqueeze(1)
            context, attn_weights = self.attention(rnn_out, mask)
        else:
            # RNN: use output at actual last timestep
            idx = (seq_lengths.clamp(min=1) - 1).unsqueeze(1).unsqueeze(2).expand(-1, 1, rnn_out.size(2))
            context = rnn_out.gather(1, idx).squeeze(1)
            attn_weights = None

        # Combine with global features
        combined = torch.cat([context, global_features], dim=-1)

        shared = self.shared_fc(combined)

        intent_logits = self.intent_head(shared)
        category_prefs = self.category_head(shared)
        purchase_prob = torch.sigmoid(self.purchase_head(shared))

        return intent_logits, category_prefs, purchase_prob, attn_weights


class BehaviorModelLoss(nn.Module):
    """Combined loss for multi-task training."""

    def __init__(self, intent_weight=1.0, category_weight=0.5, purchase_weight=1.0):
        super().__init__()
        self.intent_weight = intent_weight
        self.category_weight = category_weight
        self.purchase_weight = purchase_weight

        self.intent_loss = nn.CrossEntropyLoss()
        self.category_loss = nn.CrossEntropyLoss()
        self.purchase_loss = nn.BCELoss()

    def forward(
        self, intent_logits, category_prefs, purchase_prob,
        intent_targets, category_targets, purchase_targets,
    ):
        loss_intent = self.intent_loss(intent_logits, intent_targets)
        loss_category = self.category_loss(category_prefs, category_targets)
        loss_purchase = self.purchase_loss(
            purchase_prob.squeeze(-1), purchase_targets.float()
        )

        total = (
            self.intent_weight * loss_intent
            + self.category_weight * loss_category
            + self.purchase_weight * loss_purchase
        )

        return total, {
            'intent_loss': loss_intent.item(),
            'category_loss': loss_category.item(),
            'purchase_loss': loss_purchase.item(),
            'total_loss': total.item(),
        }
