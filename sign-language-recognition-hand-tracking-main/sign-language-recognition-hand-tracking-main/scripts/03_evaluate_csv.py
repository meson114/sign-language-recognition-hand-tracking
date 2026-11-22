"""來源：原始 csv validation.py，配合中心化模型補齊 CSV 分類測試。

保留逐部 CSV 建立序列、比較預測與標籤、輸出結果的做法。
修正：使用訓練時的 scaler，不在測試端 fit；與 validation.py 一樣
平均各視窗機率。預設只評估 02 保存的測試影片，避免把回測當成測試。
"""
import argparse
import csv
import hashlib
import json
from pathlib import Path
from project_config import KEYPOINT_DIR, MODEL_DIR, OUTPUT_DIR, ACTION_LABELS
from project_config import video_identity, read_keypoints, transform_data, load_model_and_scaler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--csv-dir", type=Path, default=KEYPOINT_DIR)
    parser.add_argument("--split", choices=["test", "all"], default="test")
    args = parser.parse_args()
    import numpy as np
    from sklearn.metrics import confusion_matrix
    model, scaler = load_model_and_scaler()
    selected, hashes = None, {}
    if args.split == "test":
        if not (MODEL_DIR / "splits.json").exists():
            parser.error("舊模型沒有測試清單；請先跑 02，或用 --split all 做資料回測。")
        selected = set(json.loads((MODEL_DIR / "splits.json").read_text(encoding="utf-8"))["test"])
        hashes = {r["video_id"]: r["sha256"] for r in json.loads((MODEL_DIR / "dataset_manifest.json").read_text(encoding="utf-8"))}
    paths = {}
    for path in sorted(args.csv_dir.glob("*.csv")):
        video_id, _ = video_identity(path.name)
        if selected is not None and video_id not in selected:
            continue
        if video_id in paths:
            raise ValueError(f"影片有重複 CSV：{video_id}")
        paths[video_id] = path
    if selected is not None and set(paths) != selected:
        raise FileNotFoundError(f"缺少測試 CSV：{sorted(selected - set(paths))}")
    rows, skipped = [], []
    for video_id, path in paths.items():
        if hashes and hashlib.sha256(path.read_bytes()).hexdigest() != hashes[video_id]:
            raise ValueError(f"CSV 在訓練後被變更：{path}，請恢復原檔或重新訓練。")
        _, label, values = read_keypoints(path)
        if len(values) < 60:
            skipped.append(path.name)
            continue
        sequences = transform_data(scaler.transform(values))
        probabilities = model.predict(sequences, batch_size=32, verbose=0).mean(axis=0)
        predicted = int(probabilities.argmax())
        rows.append({"video_id": video_id, "true_class_id": label + 1,
                     "predicted_class_id": predicted + 1,
                     "gesture_name": ACTION_LABELS[f"{predicted + 1:03d}"],
                     "confidence": float(probabilities[predicted]), "correct": predicted == label})
    if not rows or (selected is not None and skipped):
        raise ValueError("沒有有效資料，或獨立測試 CSV 不足 60 列。")
    output = OUTPUT_DIR / f"csv_{args.split}"
    output.mkdir(parents=True, exist_ok=True)
    with (output / "predictions.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    report = {"split": args.split, "videos": len(rows), "correct": sum(r["correct"] for r in rows),
              "video_top1_accuracy": sum(r["correct"] for r in rows) / len(rows), "skipped": skipped,
              "note": "獨立影片測試；尚未隔離受試者" if args.split == "test" else "資料回測，可能包含訓練影片，不能當作獨立測試準確率"}
    (output / "metrics.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    matrix = confusion_matrix([r["true_class_id"] for r in rows], [r["predicted_class_id"] for r in rows], labels=range(1, 65))
    np.savetxt(output / "confusion_matrix.csv", matrix, delimiter=",", fmt="%d")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"混淆矩陣的列／欄皆依動作編號 001～064 排列。結果：{output}")


if __name__ == "__main__":
    main()
