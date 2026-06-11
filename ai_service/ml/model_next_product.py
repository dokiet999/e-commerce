"""RNN/LSTM/BiLSTM model for next-product prediction."""

import torch
import torch.nn as nn


class NextProductModel(nn.Module):
    """Predict the next product from a sequence of product behavior events."""

    def __init__(
        self,
        num_products,
        num_actions,
        num_categories,
        num_devices,
        num_output_products=None,
        product_embed_dim=32,
        action_embed_dim=12,
        category_embed_dim=12,
        device_embed_dim=8,
        hidden_size=64,
        num_layers=1,
        dropout=0.3,
        model_type='lstm',
    ):
        super().__init__()
        if model_type not in ('rnn', 'lstm', 'bilstm'):
            raise ValueError("model_type must be one of: rnn, lstm, bilstm")

        self.model_type = model_type
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        self.num_output_products = num_output_products or num_products

        self.product_embedding = nn.Embedding(
            num_products, product_embed_dim, padding_idx=0
        )
        self.action_embedding = nn.Embedding(
            num_actions, action_embed_dim, padding_idx=0
        )
        self.category_embedding = nn.Embedding(
            num_categories, category_embed_dim, padding_idx=0
        )
        self.device_embedding = nn.Embedding(
            num_devices, device_embed_dim, padding_idx=0
        )

        input_size = (
            product_embed_dim + action_embed_dim
            + category_embed_dim + device_embed_dim
        )
        recurrent_dropout = dropout if num_layers > 1 else 0.0

        if model_type == 'rnn':
            self.rnn = nn.RNN(
                input_size=input_size,
                hidden_size=hidden_size,
                num_layers=num_layers,
                batch_first=True,
                dropout=recurrent_dropout,
            )
            output_size = hidden_size
        else:
            self.rnn = nn.LSTM(
                input_size=input_size,
                hidden_size=hidden_size,
                num_layers=num_layers,
                batch_first=True,
                dropout=recurrent_dropout,
                bidirectional=(model_type == 'bilstm'),
            )
            output_size = hidden_size * 2 if model_type == 'bilstm' else hidden_size

        self.dropout = nn.Dropout(dropout)
        self.output = nn.Linear(output_size, self.num_output_products)

    def forward(self, product_ids, actions, categories, devices, seq_lengths):
        product_emb = self.product_embedding(product_ids)
        action_emb = self.action_embedding(actions)
        category_emb = self.category_embedding(categories)
        device_emb = self.device_embedding(devices)

        seq_input = torch.cat(
            [product_emb, action_emb, category_emb, device_emb],
            dim=-1,
        )

        safe_lengths = seq_lengths.cpu().clamp(min=1)
        packed = nn.utils.rnn.pack_padded_sequence(
            seq_input,
            safe_lengths,
            batch_first=True,
            enforce_sorted=False,
        )
        packed_output, _ = self.rnn(packed)
        rnn_output, _ = nn.utils.rnn.pad_packed_sequence(
            packed_output,
            batch_first=True,
            total_length=product_ids.size(1),
        )

        last_indices = (
            seq_lengths.clamp(min=1) - 1
        ).view(-1, 1, 1).expand(-1, 1, rnn_output.size(-1))
        context = rnn_output.gather(1, last_indices).squeeze(1)
        logits = self.output(self.dropout(context))
        return logits
