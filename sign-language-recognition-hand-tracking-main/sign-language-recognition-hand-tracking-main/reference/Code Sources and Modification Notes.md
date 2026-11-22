# Code Sources and Modification Notes

This repository preserves the organized main pipeline. Raw experimental scripts, per-file diffs, original backups, legacy models, and legacy reports remain solely on the project owner's local machine and are not publicly uploaded.

| Organized Version | Original Project Source | Key Adjustments |
|---|---|---|
| `scripts/01_extract_keypoints.py` | `new extract.py` | Preserves wrist-centering and CSV format; relative paths, per-video tracker reset, unified single-hand handling |
| `scripts/02_train.py` | `train.py` | `build_model` matches the original; fixes grouping by video first, fitting the scaler only on training data, then windowing |
| `scripts/03_evaluate_csv.py` | `csv validation.py`, `validation.py` | Aligns with centered models, loads training scaler, averages window probabilities, uses held-out test videos by default |
| `scripts/04_predict_videos.py` | `validation.py` | Unifies model pairing and data rules, resets tracker per video |
| `scripts/05_webcam.py` | `untitled9.py` | Preserves confidence threshold and stability logic, unifies single-hand and model pairing, makes voice output optional |
| `scripts/project_config.py` | Duplicate path, feature, windowing, and loading logic from original scripts | Shared helper module; adds CSV and model dimension checks, does not include new models |
| `leap_unity/python/gesture_sender.py` | `gesture_sender.py` | Preserves Listener, palm coordinates, JSON, and fist logic; adds connection management and left/right hand labels |
| `leap_unity/unity/PythonToUnityReceiver.cs` | Active class from `PythonToUnityReceiver.cs` | Preserves TCP / JSON and object movement; adds disconnect handling, latest coordinates, and left/right hand routing |

`reference/action_labels.json` is taken from the 64-class mapping in the original `new extract.py`. The initial model and scaler in `models/current/` were selected based on output names from the original `train.py` and were not retrained during organization.

`leap_unity/vendor/` contains the modern Leap API / binding source code referenced by the main pipeline, retained for execution and environment maintenance; it is not a backup of various test scripts from the original project.
