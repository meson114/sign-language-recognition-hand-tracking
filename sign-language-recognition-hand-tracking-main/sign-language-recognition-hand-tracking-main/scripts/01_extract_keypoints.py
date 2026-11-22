"""來源：原始 new extract.py。影片 → 手腕中心化 → 63 維 CSV。
補上相對路徑、每部影片重設追蹤器，統一只取第一隻手。
未偵測到手就略過，保留原始擷取規則；60 列為 60 次有效偵測，
不保證為原影片連續 60 幀。本次沒有改為雙手 126 維模型。
"""
import os
from pathlib import Path
BASE_DIR = Path(__file__).resolve().parents[1]

import cv2
import csv
import numpy as np
import mediapipe as mp
from project_config import VIDEO_DIR, KEYPOINT_DIR

# 手勢標籤對應表
action_labels = {
    "001": "Opaque", "002": "Red", "003": "Green", "004": "Yellow",
    "005": "Bright", "006": "Light-blue", "007": "Colors", "008": "Pink",
    "009": "Women", "010": "Enemy", "011": "Son", "012": "Man",
    "013": "Away", "014": "Drawer", "015": "Born", "016": "Learn",
    "017": "Call", "018": "Skimmer", "019": "Bitter", "020": "Sweet milk",
    "021": "Milk", "022": "Water", "023": "Food", "024": "Argentina",
    "025": "Uruguay", "026": "Country", "027": "Last name", "028": "Where",
    "029": "Mock", "030": "Birthday", "031": "Breakfast", "032": "Photo",
    "033": "Hungry", "034": "Map", "035": "Coin", "036": "Music",
    "037": "Ship", "038": "None", "039": "Name", "040": "Patience",
    "041": "Perfume", "042": "Deaf", "043": "Trap", "044": "Rice",
    "045": "Barbecue", "046": "Candy", "047": "Chewing-gum", "048": "Spaghetti",
    "049": "Yogurt", "050": "Accept", "051": "Thanks", "052": "Shut down",
    "053": "Appear", "054": "To land", "055": "Catch", "056": "Help",
    "057": "Dance", "058": "Bathe", "059": "Buy", "060": "Copy",
    "061": "Run", "062": "Realize", "063": "Give", "064": "Find"
}

# MediaPipe 初始化
mp_hands = mp.solutions.hands


# 中心化函數：以第0點（手腕）為中心
def center_keypoints(landmarks):
    origin = landmarks[0]
    return [[x - origin[0], y - origin[1], z - origin[2]] for x, y, z in landmarks]

# 資料夾設定
video_dir = str(VIDEO_DIR)
output_dir = str(KEYPOINT_DIR)
os.makedirs(output_dir, exist_ok=True)
video_list = [f for f in os.listdir(video_dir) if f.endswith(".mp4")]
if not video_list:
    raise FileNotFoundError(f"找不到 mp4 影片：{video_dir}")

# 開始逐一處理影片
for video_file in sorted(video_list):
    # 每部影片建立獨立追蹤狀態。
    hands = mp_hands.Hands(
        static_image_mode=False,
        max_num_hands=1,
        min_detection_confidence=0.6,
        min_tracking_confidence=0.6
    )
    video_id = os.path.splitext(video_file)[0]
    action_id = video_id.split('_')[0]
    gesture = action_labels.get(action_id, "")
    video_path = os.path.join(video_dir, video_file)
    output_csv = os.path.join(output_dir, f"{video_id}.csv")

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"❌ 無法讀取影片：{video_file}")
        hands.close()
        cap.release()
        continue

    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        header = ['video_id', 'frame_index', 'action', 'gesture_name'] + [f"{axis}{i}" for i in range(21) for axis in "xyz"]
        writer.writerow(header)

        frame_index = 0
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break

            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            result = hands.process(frame_rgb)

            if result.multi_hand_landmarks:
                hand = result.multi_hand_landmarks[0]
                if len(hand.landmark) == 21:
                    landmarks = [[lm.x, lm.y, lm.z] for lm in hand.landmark]
                    centered = center_keypoints(landmarks)
                    flat = [coord for point in centered for coord in point]
                    writer.writerow([video_id, frame_index, int(action_id), gesture] + flat)

            frame_index += 1

    cap.release()
    hands.close()
    print(f"✅ 已完成影片 {video_file} ➜ 儲存至 {output_csv}")
