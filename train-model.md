Dùng file data_user500.csv vừa tạo, hãy xây dựng 3 mô hình deep learning để phân loại hành vi người dùng (cột action).

Yêu cầu chi tiết:

**Bước 1 - Tiền xử lý:**
- Label encode cột action thành số (target)
- Encode các cột: device, category, product_id
- Tạo sequences theo từng user_id (mỗi user là 1 chuỗi hành vi)
- Padding sequences về cùng độ dài
- Chia train/test = 80/20

**Bước 2 - Xây dựng 3 mô hình với Keras/TensorFlow:**
1. RNN đơn giản (SimpleRNN)
2. LSTM
3. Bidirectional LSTM (biLSTM)

Mỗi mô hình có cấu trúc:
- Embedding layer
- RNN/LSTM/biLSTM layer (64 units)
- Dropout(0.3)
- Dense layer output (softmax)
- Optimizer: Adam, Loss: categorical_crossentropy

**Bước 3 - Đánh giá:**
- In Accuracy, Precision, Recall, F1-score cho cả 3 mô hình
- Vẽ biểu đồ so sánh accuracy và loss (training history) cho 3 mô hình
- Vẽ Confusion Matrix cho mô hình tốt nhất
- Kết luận bằng lời: mô hình nào tốt nhất và tại sao
- Lưu mô hình tốt nhất thành file model_best.h5