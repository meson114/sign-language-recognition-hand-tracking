"""來源：原始 validation.py。影片 → 中心化 → 訓練 scaler → 分類。
補上相對路徑、模型配對、每部影片重設追蹤器，未偵測到手則略過，
與擷取端保持一致。此處回測全部影片，不等於獨立測試集準確率。
"""
import os
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parents[1]

import cv2
import csv
import numpy as np
import joblib
from tensorflow.keras.models import load_model
import mediapipe as mp
from project_config import load_model_and_scaler, VIDEO_DIR, MODEL_PATH, SCALER_PATH, OUTPUT_DIR

# 參數
video_dir = str(VIDEO_DIR)
model_path = str(MODEL_PATH)
scaler_path = str(SCALER_PATH)
output_csv_dir = str(OUTPUT_DIR / "centered_keypoints")
result_csv_path = str(OUTPUT_DIR / "centered_prediction_results.csv")
os.makedirs(output_csv_dir, exist_ok=True)

# 64 個手勢名稱
gesture_names = [f"Gesture {i}" for i in range(64)]

# 載入模型與 scaler
model, scaler = load_model_and_scaler()
print("✅ 已載入模型與 scaler")

# 初始化 MediaPipe
mp_hands = mp.solutions.hands


# 中心化
def center_keypoints(landmarks):
    origin = landmarks[0]
    return [[x - origin[0], y - origin[1], z - origin[2]] for x, y, z in landmarks]

# 建構序列
def transform_data(data, length=60, step=15):
    n = (len(data) - length) // step + 1
    return np.array([data[i:i+length] for i in range(0, len(data) - length + 1, step)]) if n > 0 else None

# 取得標籤
def get_true_label(filename):
    try:
        return int(filename.split('_')[0]) - 1
    except:
        return None

# 擷取影片手部資料
def extract_keypoints(video_path):
    hands = mp_hands.Hands(static_image_mode=False, max_num_hands=1,
                           min_detection_confidence=0.6, min_tracking_confidence=0.6)
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        hands.close()
        cap.release()
        raise OSError(f"無法開啟影片：{video_path}")
    keypoints = []
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result = hands.process(rgb)
        if result.multi_hand_landmarks:
            lm = result.multi_hand_landmarks[0]
            landmarks = [[p.x, p.y, p.z] for p in lm.landmark]
            centered = center_keypoints(landmarks)
            keypoints.append(np.array(centered).flatten())
        # 與 01 一致，未偵測到手就略過，不另插入零向量。
    cap.release()
    hands.close()
    return np.array(keypoints)

# 預測影片
def predict_video(video_path, filename):
    keypoints = extract_keypoints(video_path)
    if len(keypoints) < 60:
        print(f"⚠ {filename} 幀數不足")
        return None, None, None
    normalized = scaler.transform(keypoints)
    sequences = transform_data(normalized)
    if sequences is None:
        return None, None, None
    preds = model.predict(sequences)
    avg_probs = np.mean(preds, axis=0)
    return np.argmax(avg_probs), avg_probs, keypoints

# 開始預測
video_files = sorted(f for f in os.listdir(video_dir) if f.endswith(".mp4"))
if not video_files:
    raise FileNotFoundError(f"找不到 mp4 影片：{video_dir}")
with open(result_csv_path, 'w', newline='', encoding='utf-8') as f:
    csv.writer(f).writerow(['Video Name', 'True Label', 'Predicted Label', 'Probabilities'])

correct = total = 0

for i, video_file in enumerate(video_files, 1):
    path = os.path.join(video_dir, video_file)
    true_label = get_true_label(video_file)
    if true_label is None or true_label >= 64:
        print(f"⚠ {video_file} 標籤無效，跳過")
        continue

    pred_class, probs, keypoints = predict_video(path, video_file)
    if pred_class is not None:
        # 儲存每部影片對應的中心化關鍵點 CSV
        csv_path = os.path.join(output_csv_dir, f"{os.path.splitext(video_file)[0]}_centered.csv")
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow([f'{axis}{i}' for i in range(21) for axis in 'xyz'])
            writer.writerows(keypoints)

        with open(result_csv_path, 'a', newline='', encoding='utf-8') as f:
            csv.writer(f).writerow([video_file, true_label, pred_class, probs.tolist()])

        if pred_class == true_label:
            correct += 1
        total += 1

        print(f"📊 {video_file} ➜ 預測：{gesture_names[pred_class]} (正確：{gesture_names[true_label]})")

# 顯示準確率
if total > 0:
    acc = correct / total * 100
    print(f"\n🎯 預測準確率：{acc:.2f}% ({correct}/{total})")
else:
    print("⚠ 無任何有效預測")
