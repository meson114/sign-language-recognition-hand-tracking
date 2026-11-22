# Sign Language Recognition and Hand Tracking System

This project includes two modules: recognizing 64 sign language classes from LSA64 using MediaPipe and CNN-LSTM, and displaying real-time dual-hand palm positions through Leap Motion, Python, TCP, and Unity.

The code is organized from the original project source code, preserving the original CNN-LSTM model architecture while adding comments and fixing data, model pairing, and communication integration. See [Source Notes](reference/程式來源與修改說明.md) for code sources and modifications.

## Repository Contents

```text
scripts/               Sign language recognition pipeline 01–05 and shared configuration
models/current/        Existing centered model and paired scaler
leap_unity/            Leap sender, Unity receiver, and required API source code
reference/             Class labels, environment, source, and verification notes
```

Uses camera `0` by default; press `Q` to quit. If your camera uses a different index, update `VideoCapture(0)`. Speech synthesis is disabled by default; set `ENABLE_SPEECH` to `True` when needed and use an environment that already has `pyttsx3` installed.

The provided `hand_gesture_model_centered1.h5` and `scaler1.save` are the original paired artifacts, not results retrained during this cleanup. Whether the legacy model loads directly still depends on the original package versions.

## Retraining and Testing from Videos

This repository does not include `data/`. Create `data/videos/` yourself and place the LSA64 videos inside with filenames such as `001_001_001.mp4`. The three numeric segments represent the action, subject, and repetition index in order.

Wait for the previous script to finish before running the next one:

| Order | Command | Function and Output |
| --- | --- | --- |
| 01 | `python scripts\01_extract_keypoints.py` | Extracts 21 single-hand landmarks, centers them at the wrist, and saves 63-dimensional coordinates to `data/training_keypoints/` |
| 02 | `python scripts\02_train.py` | Trains the CNN-LSTM and saves the model, scaler, test list, training curves, and test-window confusion matrix |
| 03 | `python scripts\03_evaluate_csv.py` | Uses only held-out test video CSVs and outputs video-level Top-1 accuracy, prediction list, and confusion matrix |
| 04 Optional | `python scripts\04_predict_videos.py` | Re-extracts features from source videos and runs backtesting across all videos |
| 05 Optional | `python scripts\05_webcam.py` | Opens the camera for real-time recognition |

All paths are resolved relative to the project root, with shared configuration in `scripts/project_config.py`. Steps 04 and 05 are separate testing modes and do not depend on each other.

### Data and Training Configuration

- Feature layout: `x0,y0,z0,...,x20,y20,z20`. Frames where no hand is detected are skipped following the original extraction rule, so 60 rows are not guaranteed to correspond to 60 consecutive frames in the source video.
- Time window length is 60 with a stride of 15; each class requires at least 5 videos containing at least 60 rows of valid data.
- Split videos first into roughly 60% train, 20% validation, and 20% test sets, then slice windows separately. Fit the scaler exclusively on the training videos.
- Preserves the original Conv1D → LSTM → Dense → Softmax architecture, with defaults of 30 epochs, batch size 32, and EarlyStopping patience 5.
- Step `02` overwrites the model and scaler in `models/current/`. Back up the provided weights first if you want to keep them.

Results from `03` are saved under `outputs/csv_test/`, including `predictions.csv`, `metrics.json`, and `confusion_matrix.csv`. Each video selects Top-1 using averaged window probabilities, which uses a different statistical unit than the per-window confusion matrix from `02`.

When using the legacy model to backtest self-prepared centered CSVs, the legacy model has no separate test manifest, so you must explicitly specify:

```powershell
python scripts\03_evaluate_csv.py --split all --csv-dir data\training_keypoints
```

`all` and step `04` may include training videos, so they cannot be treated as standalone test accuracy. `03` outputs class labels as `1–64`, while `04` keeps the original `0–63` numbering.

## Leap Motion and Unity

This workflow does not require training the CNN-LSTM first. Following the [Leap/Unity Instructions](leap_unity/README.md), start the Unity receiver first, then run:

```powershell
python leap_unity\python\gesture_sender.py
```

Sends to `127.0.0.1:8054` by default. The required modern Python API source code is included with the project, but you still need the existing Ultraleap SDK, CFFI bindings, tracking service, and hardware.

This repository provides the Unity receiver script, not a full Unity project, scene, or interactive assets. The script can move left and right hand objects separately, currently sending palm positions without full finger skeleton animation.

## Verification and Limitations

The cleaned version has undergone syntax checks, original model architecture comparisons, and simulated JSON/disconnection cleanup checks. It has not yet been trained in the original environment, run on a live camera, or tested with a Unity/Leap device; see [Verification Notes](reference/驗證紀錄.md) and [Environment Notes](reference/套件與環境說明.md) for details.

The sign language model still takes 63-dimensional single-hand input, while dual-hand tracking is a separate module. Fixing the data split affects accuracy, and the ~87% figure noted in the project description was not reproduced or re-measured here. There is currently no code sending CNN-LSTM recognition text into the Unity scene.
