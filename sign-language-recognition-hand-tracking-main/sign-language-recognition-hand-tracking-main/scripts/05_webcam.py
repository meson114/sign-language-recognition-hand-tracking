"""來源：原始 untitled9.py。攝影機即時辨識，按 Q 結束。
統一模型配對與單手設定；語音改為選用，預設不用額外的 pyttsx3。
原模型仍為單手 63 維，不是雙手融合辨識。
"""
import cv2
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parents[1]

import numpy as np
import mediapipe as mp
import joblib
import time
from collections import deque
from tensorflow.keras.models import load_model
from project_config import load_model_and_scaler

# 1. 載入模型與 scaler（需確認路徑正確）
model, scaler = load_model_and_scaler()

# 2. 標籤名稱
action_labels = {
    str(i + 1).zfill(3): name for i, name in enumerate([
        "Opaque", "Red", "Green", "Yellow", "Bright", "Light-blue", "Colors", "Pink",
        "Women", "Enemy", "Son", "Man", "Away", "Drawer", "Born", "Learn", "Call", "Skimmer",
        "Bitter", "Sweet milk", "Milk", "Water", "Food", "Argentina", "Uruguay", "Country",
        "Last name", "Where", "Mock", "Birthday", "Breakfast", "Photo", "Hungry", "Map",
        "Coin", "Music", "Ship", "None", "Name", "Patience", "Perfume", "Deaf", "Trap", "Rice",
        "Barbecue", "Candy", "Chewing-gum", "Spaghetti", "Yogurt", "Accept", "Thanks", "Shut down",
        "Appear", "To land", "Catch", "Help", "Dance", "Bathe", "Buy", "Copy", "Run", "Realize",
        "Give", "Find"
    ])
}

# 3. 初始化 MediaPipe
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(static_image_mode=False, max_num_hands=1, min_detection_confidence=0.6, min_tracking_confidence=0.6)
mp_drawing = mp.solutions.drawing_utils

# 4. 初始化資料
sequence_L, sequence_R = [], []
SEQUENCE_LENGTH = 60
sentence = deque(maxlen=5)
ENABLE_SPEECH = False  # 需要朗讀再改 True，使用原本裝有 pyttsx3 的環境。
engine = None
if ENABLE_SPEECH:
    import pyttsx3
    engine = pyttsx3.init()

prev_label = None
stability_count = 0
STABLE_THRESHOLD = 5

cap = cv2.VideoCapture(0)
if not cap.isOpened():
    hands.close()
    cap.release()
    raise OSError("無法開啟攝影機 0，請確認相機未被占用，或更改裝置編號。")
prev_time = time.time()

# 正規化：中心化並使用 scaler
def center_keypoints(landmarks):
    origin = landmarks[0]
    return [[x - origin[0], y - origin[1], z - origin[2]] for x, y, z in landmarks]

# 主迴圈
while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        print("❌ 無法讀取攝影機影像")
        break

    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    result = hands.process(frame_rgb)

    if result.multi_hand_landmarks:
        for hand_idx, hand_landmarks in enumerate(result.multi_hand_landmarks):
            mp_drawing.draw_landmarks(frame, hand_landmarks, mp_hands.HAND_CONNECTIONS)
            keypoints = [[lm.x, lm.y, lm.z] for lm in hand_landmarks.landmark]
            centered = center_keypoints(keypoints)
            flattened = np.array(centered).flatten().reshape(1, -1)
            normalized = scaler.transform(flattened).flatten()

            if hand_idx == 0:
                sequence_L.append(normalized)
                active_seq = sequence_L
            else:
                sequence_R.append(normalized)
                active_seq = sequence_R

            if len(active_seq) == SEQUENCE_LENGTH:
                input_data = np.array([active_seq])
                prediction = model.predict(input_data, verbose=0)
                predicted_class = np.argmax(prediction)
                confidence = np.max(prediction)
                label_number = str(predicted_class + 1).zfill(3)
                label_name = action_labels.get(label_number, "Unknown")

                if confidence > 0.7:
                    if label_name == prev_label:
                        stability_count += 1
                    else:
                        prev_label = label_name
                        stability_count = 1

                    if stability_count == STABLE_THRESHOLD:
                        if not sentence or sentence[-1] != label_name:
                            sentence.append(label_name)
                            if engine is not None:
                                engine.say(label_name)
                                engine.runAndWait()

                    cv2.putText(frame, f"{label_name} ({confidence:.2f})",
                                (10, 30 + hand_idx * 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
                else:
                    stability_count = 0
                    prev_label = None
                    cv2.putText(frame, "Unknown",
                                (10, 30 + hand_idx * 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

                active_seq.pop(0)
    else:
        sequence_L, sequence_R = [], []
        prev_label = None
        stability_count = 0

    # 顯示文字
    text = " ".join(sentence)
    cv2.rectangle(frame, (0, frame.shape[0] - 50), (frame.shape[1], frame.shape[0]), (0, 0, 0), -1)
    cv2.putText(frame, text, (10, frame.shape[0] - 10),
                cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)

    # 顯示 FPS
    curr_time = time.time()
    fps = 1 / (curr_time - prev_time)
    prev_time = curr_time

    # 新增：右上角座標
    fps_text = f"FPS: {fps:.2f}"
    (text_w, text_h), _ = cv2.getTextSize(fps_text, cv2.FONT_HERSHEY_SIMPLEX, 0.8, 2)
    cv2.putText(frame, fps_text,
            (frame.shape[1] - text_w - 10, 25),
            cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 255, 255), 2)


    cv2.imshow('Hand Gesture Recognition', frame)
    if cv2.waitKey(10) & 0xFF == ord('q'):
        break

cap.release()
hands.close()
cv2.destroyAllWindows()
