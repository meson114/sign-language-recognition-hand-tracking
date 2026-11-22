"""來源：原始 train.py，保留原本 CNN-LSTM 模型架構與訓練參數。
先按影片切分訓練／驗證／測試，只用訓練資料擬合 MinMaxScaler，再切
60 列視窗，避免重疊視窗及 scaler 洩漏測試資料。此修正會影響準確率，
新流程的結果不能直接當作原本約 87% 的重現。
"""
import os
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parents[1]

import pandas as pd
import numpy as np
import matplotlib
matplotlib.use("Agg")  # 直接存圖，不用手動關閉視窗。
import matplotlib.pyplot as plt
import joblib
import json
import hashlib
from project_config import read_keypoints, transform_data, KEYPOINT_DIR, MODEL_DIR
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import MinMaxScaler
from sklearn.metrics import confusion_matrix, ConfusionMatrixDisplay
from tensorflow.keras.utils import to_categorical
from tensorflow.keras import models, layers
from tensorflow.keras.callbacks import EarlyStopping

# 資料夾路徑
data_dir = str(KEYPOINT_DIR)
model_dir = MODEL_DIR
os.makedirs(model_dir, exist_ok=True)
file_list = [f for f in os.listdir(data_dir) if f.endswith(".csv")]

# 沿用原始特徵順序 x0,y0,z0,...,x20,y20,z20。
# 共用讀取函數也能由檔名還原舊 CSV 缺少的 action/video_id。
records, skipped = [], []
for file in sorted(file_list):
    path = Path(data_dir) / file
    video_id, label, values = read_keypoints(path)
    if len(values) < 60:
        skipped.append(file)
        continue
    records.append({"path": path, "video_id": video_id, "label": label, "values": values})
counts = np.bincount([r["label"] for r in records], minlength=64)
if np.any(counts < 5):
    raise ValueError("每類至少需要 5 部有 60 列的影片；請先完成 01 的全部擷取。")
if len({r["video_id"] for r in records}) != len(records):
    raise ValueError("有重複影片 ID，請勿混放同一影片的不同 CSV 版本。")
labels = np.array([r["label"] for r in records])
indices = np.arange(len(records))
# 60% 訓練、20% 驗證、20% 測試；同一部影片只屬於其中一組。
trainval_idx, test_idx = train_test_split(indices, test_size=0.2, stratify=labels, random_state=42)
train_idx, val_idx = train_test_split(trainval_idx, test_size=0.25, stratify=labels[trainval_idx], random_state=42)
scaler = MinMaxScaler()
for index in train_idx:
    scaler.partial_fit(records[int(index)]["values"])

def prepare_sequences(selected):
    xs, ys = [], []
    for index in selected:
        record = records[int(index)]
        sequences = transform_data(scaler.transform(record["values"]))
        xs.append(sequences)
        ys.append(np.full(len(sequences), record["label"]))
    return np.concatenate(xs), to_categorical(np.concatenate(ys), num_classes=64)

X_train, y_train = prepare_sequences(train_idx)
X_val, y_val = prepare_sequences(val_idx)
print(f"訓練視窗 {X_train.shape}；驗證視窗 {X_val.shape}；保留測試影片 {len(test_idx)} 部")

# 模型架構
def build_model(input_shape, num_classes):
    model = models.Sequential([
        layers.Conv1D(64, 3, activation='relu', input_shape=input_shape),
        layers.MaxPooling1D(1),
        layers.Conv1D(128, 3, activation='relu'),
        layers.MaxPooling1D(2),
        layers.Conv1D(256, 3, activation='relu'),
        layers.MaxPooling1D(2),
        layers.LSTM(128, return_sequences=True),
        layers.LSTM(64),
        layers.Dropout(0.5),
        layers.Dense(128, activation='relu'),
        layers.Dense(num_classes, activation='softmax')
    ])
    model.compile(optimizer='adam', loss='categorical_crossentropy', metrics=['accuracy'])
    return model

# 固定亂數種子，方便比較重跑結果；不同環境仍可能有數值差異。
from tensorflow.keras.utils import set_random_seed
set_random_seed(42)
# 訓練模型
model = build_model((60, 63), 64)
early_stop = EarlyStopping(monitor='val_loss', patience=5, restore_best_weights=True)

history = model.fit(
    X_train, y_train,
    epochs=30,
    batch_size=32,
    validation_data=(X_val, y_val),
    callbacks=[early_stop]
)

# 儲存模型
os.makedirs(model_dir, exist_ok=True)
# 先完成兩個暫存檔，再替換正式配對，避免序列化失敗先破壞舊配對。
model.save(str(model_dir / "pending_model.h5"))
joblib.dump(scaler, str(model_dir / "pending_scaler.save"))
(model_dir / "pending_model.h5").replace(model_dir / "hand_gesture_model_centered1.h5")
(model_dir / "pending_scaler.save").replace(model_dir / "scaler1.save")
splits = {name: [records[int(i)]["video_id"] for i in group] for name, group in
          [("train", train_idx), ("validation", val_idx), ("test", test_idx)]}
(model_dir / "splits.json").write_text(json.dumps(splits, indent=2), encoding="utf-8")
manifest = [{"video_id": r["video_id"], "file": r["path"].name,
             "sha256": hashlib.sha256(r["path"].read_bytes()).hexdigest()} for r in records]
(model_dir / "dataset_manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
(model_dir / "skipped_short_csv.json").write_text(json.dumps(skipped, indent=2), encoding="utf-8")
print(f"模型、scaler 與資料切分已儲存：{model_dir}")

# 訓練曲線
plt.figure(figsize=(12, 5))
plt.subplot(1, 2, 1)
plt.plot(history.history['accuracy'], label='Train Acc')
plt.plot(history.history['val_accuracy'], label='Val Acc')
plt.title('Accuracy Over Epochs')
plt.legend()
plt.grid(True)

plt.subplot(1, 2, 2)
plt.plot(history.history['loss'], label='Train Loss')
plt.plot(history.history['val_loss'], label='Val Loss')
plt.title('Loss Over Epochs')
plt.legend()
plt.grid(True)

plt.tight_layout()
plt.savefig(str(model_dir / "training_plot_centered1.png"))
plt.close()

# 測試影片未用於 EarlyStopping，訓練完成後才評估。
X_test, y_test = prepare_sequences(test_idx)
# 混淆矩陣
y_true = np.argmax(y_test, axis=1)
y_pred = np.argmax(model.predict(X_test), axis=1)
cm = confusion_matrix(y_true, y_pred, labels=np.arange(64))
disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=[f"{i}" for i in range(64)])
disp.plot(xticks_rotation='vertical', cmap='Blues', values_format='d')
plt.title("Confusion Matrix")
plt.tight_layout()
plt.savefig(str(model_dir / "confusion_matrix_centered.png"), dpi=300)
plt.close()
