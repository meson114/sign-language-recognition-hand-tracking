"""集中管理原始程式重複出現的路徑與資料格式，不包含新的辨識模型。

特徵順序與 new extract.py、train.py 相同：x0,y0,z0,...,x20,y20,z20。
整理後的程式都以本檔位置計算路徑，不受終端機目前目錄影響。
"""
from pathlib import Path
import csv
import json
import re

ROOT = Path(__file__).resolve().parents[1]
VIDEO_DIR = ROOT / "data/videos"
KEYPOINT_DIR = ROOT / "data/training_keypoints"
MODEL_DIR = ROOT / "models/current"
MODEL_PATH = MODEL_DIR / "hand_gesture_model_centered1.h5"
SCALER_PATH = MODEL_DIR / "scaler1.save"
OUTPUT_DIR = ROOT / "outputs"
FEATURES = [f"{axis}{i}" for i in range(21) for axis in "xyz"]
SEQUENCE_LENGTH = 60
WINDOW_STEP = 15
ACTION_LABELS = json.loads((ROOT / "reference/action_labels.json").read_text(encoding="utf-8"))


def video_identity(filename):
    """LSA64 檔名：動作編號_受試者編號_重複次數，可帶 _centered 後綴。"""
    match = re.fullmatch(r"(\d{3})_(\d{3})_(\d{3})(?:_centered)?", Path(filename).stem)
    if not match or not 1 <= int(match[1]) <= 64:
        raise ValueError(f"不符合 LSA64 命名規則：{filename}")
    return "_".join(match.groups()), int(match[1]) - 1


def read_keypoints(path):
    """讀取中心化 CSV；驗證欄位，並兼容舊存檔沒有 action/video_id 的情況。"""
    import numpy as np
    import pandas as pd
    path = Path(path)
    video_id, label = video_identity(path.name)
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        header = next(reader, [])
        if len(header) != len(set(header)) or not header:
            raise ValueError(f"CSV 標頭為空或重複：{path}")
        for line, row in enumerate(reader, 2):
            if len(row) != len(header):
                raise ValueError(f"CSV 第 {line} 行欄位數量不符：{path}")
    df = pd.read_csv(path)
    if not all(column in df for column in FEATURES):
        raise ValueError(f"缺少 63 維關鍵點欄位：{path}")
    if "action" in df and not (df["action"] == label + 1).all():
        raise ValueError(f"action 與檔名不一致：{path}")
    if "video_id" in df and not (df["video_id"] == video_id).all():
        raise ValueError(f"同一 CSV 的 video_id 不一致：{path}")
    if "frame_index" in df:
        if df["frame_index"].duplicated().any():
            raise ValueError(f"同一 CSV 出現重複幀：{path}")
        df = df.sort_values("frame_index")
    values = df[FEATURES].to_numpy(dtype=np.float32)
    if not np.isfinite(values).all():
        raise ValueError(f"CSV 包含 NaN 或無限值：{path}")
    if len(values) and not np.allclose(values[:, :3], 0, atol=1e-5):
        raise ValueError(f"手腕沒有中心化，請勿混入舊版原始座標 CSV：{path}")
    return video_id, label, values


def transform_data(data, length=SEQUENCE_LENGTH, step=WINDOW_STEP):
    """沿用原始滑動視窗：每 15 列取連續 60 列，不跨影片。"""
    import numpy as np
    if len(data) < length:
        return np.empty((0, length, 63), dtype=np.float32)
    return np.asarray([data[i:i + length] for i in range(0, len(data) - length + 1, step)], dtype=np.float32)


def load_model_and_scaler():
    """以 train.py 原本的輸出檔名配對，避免舊版混用 centered/scaler。"""
    import joblib
    from tensorflow.keras.models import load_model
    if not MODEL_PATH.is_file() or not SCALER_PATH.is_file():
        raise FileNotFoundError("缺少模型或 scaler，請先執行 02_train.py，或放回 models/current 的原模型配對。")
    model = load_model(MODEL_PATH, compile=False)
    scaler = joblib.load(SCALER_PATH)
    if tuple(model.input_shape[1:]) != (60, 63) or model.output_shape[-1] != 64:
        raise ValueError("模型規格應為 (60, 63) 輸入、64 類輸出，請檢查模型檔。")
    if getattr(scaler, "n_features_in_", None) != 63:
        raise ValueError("scaler 應使用同樣的 63 維特徵。")
    return model, scaler
