import pandas as pd
import numpy as np
import os
import warnings
warnings.filterwarnings('ignore')

from sklearn.preprocessing import LabelEncoder
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix, classification_report

import tensorflow as tf
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import (
    Embedding, SimpleRNN, LSTM, Bidirectional,
    Dense, Dropout
)
from tensorflow.keras.utils import to_categorical
from tensorflow.keras.preprocessing.sequence import pad_sequences

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import seaborn as sns

# ==============================================================================
# BƯỚC 1 - TIỀN XỬ LÝ
# ==============================================================================
print("=" * 80)
print("BƯỚC 1 - TIỀN XỬ LÝ DỮ LIỆU")
print("=" * 80)

# Đọc dữ liệu
df = pd.read_csv('data_user500.csv')
print(f"Shape: {df.shape}")
print(f"Columns: {list(df.columns)}")

# Label encode cột action (target)
le_action = LabelEncoder()
df['action_encoded'] = le_action.fit_transform(df['action'])
num_classes = len(le_action.classes_)
print(f"\nAction classes ({num_classes}): {list(le_action.classes_)}")

# Encode các cột features
le_device = LabelEncoder()
le_category = LabelEncoder()
le_product = LabelEncoder()

df['device_encoded'] = le_device.fit_transform(df['device'])
df['category_encoded'] = le_category.fit_transform(df['category'])
df['product_encoded'] = le_product.fit_transform(df['product_id'])

# Tạo feature tổng hợp cho mỗi dòng: kết hợp device + category + product thành 1 feature index
# Dùng cách: tạo combined feature index
num_devices = len(le_device.classes_)
num_categories = len(le_category.classes_)
num_products = len(le_product.classes_)

df['feature_combined'] = (
    df['product_encoded'] * (num_devices * num_categories)
    + df['category_encoded'] * num_devices
    + df['device_encoded']
    + 1  # +1 để dành index 0 cho padding
)
vocab_size = df['feature_combined'].max() + 1

print(f"Vocab size (combined features): {vocab_size}")

# Tạo sequences theo user_id
print("\nTạo sequences theo user_id...")
user_groups = df.groupby('user_id')

X_sequences = []
y_sequences = []

for user_id, group in user_groups:
    features = group['feature_combined'].values.tolist()
    actions = group['action_encoded'].values.tolist()
    X_sequences.append(features)
    y_sequences.append(actions)

# Padding sequences về cùng độ dài
max_len = max(len(seq) for seq in X_sequences)
print(f"Max sequence length: {max_len}")

X_padded = pad_sequences(X_sequences, maxlen=max_len, padding='post', value=0)
y_padded = pad_sequences(y_sequences, maxlen=max_len, padding='post', value=0)

print(f"X_padded shape: {X_padded.shape}")
print(f"y_padded shape: {y_padded.shape}")

# Reshape: mỗi timestep trong sequence là 1 sample (flatten sequences)
# Approach: dùng sequence-to-sequence prediction (mỗi user là 1 sequence)
# y cần one-hot encode
y_onehot = np.zeros((y_padded.shape[0], y_padded.shape[1], num_classes))
for i in range(y_padded.shape[0]):
    for j in range(y_padded.shape[1]):
        y_onehot[i, j, y_padded[i, j]] = 1

# Chia train/test = 80/20
X_train, X_test, y_train, y_test = train_test_split(
    X_padded, y_onehot, test_size=0.2, random_state=42
)
print(f"\nTrain: {X_train.shape[0]} users, Test: {X_test.shape[0]} users")

# Lưu y_test dạng label để đánh giá
y_test_labels = np.argmax(y_test, axis=-1).flatten()


# ==============================================================================
# BƯỚC 2 - XÂY DỰNG 3 MÔ HÌNH
# ==============================================================================
print("\n" + "=" * 80)
print("BƯỚC 2 - XÂY DỰNG 3 MÔ HÌNH")
print("=" * 80)

EMBEDDING_DIM = 32
RNN_UNITS = 64
DROPOUT_RATE = 0.3
EPOCHS = 30
BATCH_SIZE = 32


def build_simple_rnn():
    model = Sequential([
        Embedding(input_dim=vocab_size, output_dim=EMBEDDING_DIM, mask_zero=True),
        SimpleRNN(RNN_UNITS, return_sequences=True),
        Dropout(DROPOUT_RATE),
        Dense(num_classes, activation='softmax')
    ])
    model.compile(optimizer='adam', loss='categorical_crossentropy', metrics=['accuracy'])
    return model


def build_lstm():
    model = Sequential([
        Embedding(input_dim=vocab_size, output_dim=EMBEDDING_DIM, mask_zero=True),
        LSTM(RNN_UNITS, return_sequences=True),
        Dropout(DROPOUT_RATE),
        Dense(num_classes, activation='softmax')
    ])
    model.compile(optimizer='adam', loss='categorical_crossentropy', metrics=['accuracy'])
    return model


def build_bilstm():
    model = Sequential([
        Embedding(input_dim=vocab_size, output_dim=EMBEDDING_DIM, mask_zero=True),
        Bidirectional(LSTM(RNN_UNITS, return_sequences=True)),
        Dropout(DROPOUT_RATE),
        Dense(num_classes, activation='softmax')
    ])
    model.compile(optimizer='adam', loss='categorical_crossentropy', metrics=['accuracy'])
    return model


models_config = {
    'SimpleRNN': build_simple_rnn,
    'LSTM': build_lstm,
    'BiLSTM': build_bilstm,
}

histories = {}
trained_models = {}
results = {}

for name, build_fn in models_config.items():
    print(f"\n{'─' * 40}")
    print(f"Training {name}...")
    print(f"{'─' * 40}")

    model = build_fn()
    model.summary()

    history = model.fit(
        X_train, y_train,
        validation_data=(X_test, y_test),
        epochs=EPOCHS,
        batch_size=BATCH_SIZE,
        verbose=1
    )

    histories[name] = history
    trained_models[name] = model

    # Predict
    y_pred_proba = model.predict(X_test)
    y_pred_labels = np.argmax(y_pred_proba, axis=-1).flatten()

    acc = accuracy_score(y_test_labels, y_pred_labels)
    prec = precision_score(y_test_labels, y_pred_labels, average='weighted', zero_division=0)
    rec = recall_score(y_test_labels, y_pred_labels, average='weighted', zero_division=0)
    f1 = f1_score(y_test_labels, y_pred_labels, average='weighted', zero_division=0)

    results[name] = {
        'accuracy': acc,
        'precision': prec,
        'recall': rec,
        'f1_score': f1,
        'y_pred': y_pred_labels,
    }

    print(f"\n{name} Results:")
    print(f"  Accuracy : {acc:.4f}")
    print(f"  Precision: {prec:.4f}")
    print(f"  Recall   : {rec:.4f}")
    print(f"  F1-Score : {f1:.4f}")


# ==============================================================================
# BƯỚC 3 - ĐÁNH GIÁ VÀ SO SÁNH
# ==============================================================================
print("\n" + "=" * 80)
print("BƯỚC 3 - ĐÁNH GIÁ VÀ SO SÁNH")
print("=" * 80)

# Bảng so sánh
print("\n┌─────────────┬──────────┬───────────┬──────────┬──────────┐")
print("│ Model       │ Accuracy │ Precision │ Recall   │ F1-Score │")
print("├─────────────┼──────────┼───────────┼──────────┼──────────┤")
for name, r in results.items():
    print(f"│ {name:<11} │ {r['accuracy']:.4f}   │ {r['precision']:.4f}    │ {r['recall']:.4f}   │ {r['f1_score']:.4f}   │")
print("└─────────────┴──────────┴───────────┴──────────┴──────────┘")

# Tìm mô hình tốt nhất
best_name = max(results, key=lambda x: results[x]['f1_score'])
print(f"\nMô hình tốt nhất: {best_name} (F1-Score: {results[best_name]['f1_score']:.4f})")

# --- Vẽ biểu đồ Accuracy & Loss ---
fig, axes = plt.subplots(1, 2, figsize=(14, 5))

# Accuracy
for name, h in histories.items():
    axes[0].plot(h.history['accuracy'], label=f'{name} - Train')
    axes[0].plot(h.history['val_accuracy'], '--', label=f'{name} - Val')
axes[0].set_title('Model Accuracy Comparison')
axes[0].set_xlabel('Epoch')
axes[0].set_ylabel('Accuracy')
axes[0].legend()
axes[0].grid(True, alpha=0.3)

# Loss
for name, h in histories.items():
    axes[1].plot(h.history['loss'], label=f'{name} - Train')
    axes[1].plot(h.history['val_loss'], '--', label=f'{name} - Val')
axes[1].set_title('Model Loss Comparison')
axes[1].set_xlabel('Epoch')
axes[1].set_ylabel('Loss')
axes[1].legend()
axes[1].grid(True, alpha=0.3)

plt.tight_layout()
plt.savefig('training_history.png', dpi=150, bbox_inches='tight')
print("\nĐã lưu biểu đồ: training_history.png")

# --- Confusion Matrix cho mô hình tốt nhất ---
fig, ax = plt.subplots(figsize=(10, 8))
cm = confusion_matrix(y_test_labels, results[best_name]['y_pred'])
sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
            xticklabels=le_action.classes_,
            yticklabels=le_action.classes_, ax=ax)
ax.set_title(f'Confusion Matrix - {best_name} (Best Model)')
ax.set_xlabel('Predicted')
ax.set_ylabel('Actual')
plt.tight_layout()
plt.savefig('confusion_matrix.png', dpi=150, bbox_inches='tight')
print("Đã lưu biểu đồ: confusion_matrix.png")

# --- Classification Report cho mô hình tốt nhất ---
print(f"\nClassification Report - {best_name}:")
print(classification_report(y_test_labels, results[best_name]['y_pred'],
                            target_names=le_action.classes_))

# --- Lưu mô hình tốt nhất ---
best_model_path = 'model_best.h5'
trained_models[best_name].save(best_model_path)
print(f"Đã lưu mô hình tốt nhất: {best_model_path}")

# --- Kết luận ---
print("\n" + "=" * 80)
print("KẾT LUẬN")
print("=" * 80)

sorted_models = sorted(results.items(), key=lambda x: x[1]['f1_score'], reverse=True)
rank1, rank2, rank3 = sorted_models[0], sorted_models[1], sorted_models[2]

print(f"""
Sau khi huấn luyện và đánh giá 3 mô hình trên dữ liệu hành vi 500 users:

1. {rank1[0]} đạt F1-Score cao nhất: {rank1[1]['f1_score']:.4f}
2. {rank2[0]} đạt F1-Score: {rank2[1]['f1_score']:.4f}
3. {rank3[0]} đạt F1-Score: {rank3[1]['f1_score']:.4f}

=> Mô hình {best_name} được chọn là mô hình tốt nhất.

Lý do:
- {best_name} có khả năng nắm bắt ngữ cảnh chuỗi hành vi tốt hơn nhờ kiến trúc
  phù hợp cho dữ liệu sequential (chuỗi hành vi người dùng theo thời gian).
- LSTM/BiLSTM thường vượt trội hơn SimpleRNN nhờ cơ chế gate giúp ghi nhớ
  thông tin dài hạn, tránh vanishing gradient.
- BiLSTM có thêm lợi thế khi đọc chuỗi theo cả 2 chiều, giúp hiểu ngữ cảnh
  toàn diện hơn.

Các file đã lưu:
- model_best.h5          : Mô hình tốt nhất
- training_history.png   : Biểu đồ so sánh accuracy & loss
- confusion_matrix.png   : Confusion matrix mô hình tốt nhất
""")
