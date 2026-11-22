# 手語辨識與手部追蹤系統

本專題包含兩個模組：使用 MediaPipe 與 CNN-LSTM 辨識 LSA64 的 64 類手語，以及透過 Leap Motion、Python、TCP 與 Unity 呈現即時雙手掌心位置。

程式由原專題原始碼整理，保留原 CNN-LSTM 模型架構，補上註解並修正資料、模型配對及通訊銜接。程式來源與調整內容見 [來源說明](reference/程式來源與修改說明.md)。

## 儲存庫內容

```text
scripts/               手語辨識主流程 01～05 與共用設定
models/current/        原有中心化模型與配對 scaler
leap_unity/            Leap 傳送端、Unity 接收端及必要 API 原始碼
reference/             類別名稱、環境、來源與驗證說明
```

資料集、擷取後 CSV、歷史實驗程式、舊模型與舊報表未納入此儲存庫。原始備份保留於專題擁有者本機。

## 使用既有模型開啟攝影機

使用原本能運作的 Python／MediaPipe／TensorFlow 環境，在儲存庫根目錄執行：

```powershell
python scripts\05_webcam.py
```

預設使用攝影機 `0`，按 `Q` 結束。若相機在其他編號，修改 `VideoCapture(0)`。語音朗讀預設關閉，需要時將 `ENABLE_SPEECH` 改為 `True`，並使用原本裝有 `pyttsx3` 的環境。

提供的 `hand_gesture_model_centered1.h5` 與 `scaler1.save` 是原有模型配對，不是本次整理重新訓練的成果。舊模型能否直接載入仍取決於原套件版本。

## 從影片重新訓練與測試

本儲存庫不包含 `data/`。先自行建立 `data/videos/`，放入 LSA64 影片，檔名如 `001_001_001.mp4`。三段編號依序表示動作、受試者與重複次數。

等上一支程式結束，再執行下一支：

| 順序 | 指令 | 功能與輸出 |
|---|---|---|
| 01 | `python scripts\01_extract_keypoints.py` | 擷取單手 21 點，手腕中心化後將 63 維座標存入 `data/training_keypoints/` |
| 02 | `python scripts\02_train.py` | 訓練 CNN-LSTM，儲存模型、scaler、測試清單、曲線與測試視窗混淆矩陣 |
| 03 | `python scripts\03_evaluate_csv.py` | 只使用保留測試影片的 CSV，輸出影片層級 Top-1、預測清單與混淆矩陣 |
| 04 選用 | `python scripts\04_predict_videos.py` | 從原影片重新擷取特徵，回測全部影片 |
| 05 選用 | `python scripts\05_webcam.py` | 開啟攝影機進行即時辨識 |

所有路徑以專案所在位置計算，共用設定在 `scripts/project_config.py`。步驟 04、05 是不同測試方式，互不依賴。

### 資料與訓練設定

- 特徵排列：`x0,y0,z0,...,x20,y20,z20`。未偵測到手的幀沿用原擷取規則略過，因此 60 列不保證對應原影片連續 60 幀。
- 時間視窗長度 60，步距 15；每類至少需要 5 部具有 60 列有效資料的影片。
- 先按影片分成約 60% 訓練、20% 驗證、20% 測試，再分別切窗。scaler 僅使用訓練影片擬合。
- 保留原 Conv1D → LSTM → Dense → Softmax 架構，預設 30 epochs、batch size 32、EarlyStopping patience 5。
- 02 會更新 `models/current/` 的模型與 scaler。需要保留提供的權重時，請先自行備份。

03 的結果位於 `outputs/csv_test/`，包含 `predictions.csv`、`metrics.json`、`confusion_matrix.csv`。各影片以視窗平均機率選取 Top-1；與 02 的每視窗混淆矩陣是不同統計單位。

若使用原有模型回測自行準備的中心化 CSV，舊模型沒有獨立測試清單，須明確指定：

```powershell
python scripts\03_evaluate_csv.py --split all --csv-dir data\training_keypoints
```

`all` 與步驟 04 可能包含訓練影片，不能當成獨立測試準確率。03 類別輸出使用 1～64；04 沿用原版的 0～63。

## Leap Motion 與 Unity

這條流程不需要先訓練 CNN-LSTM。請依 [Leap／Unity 操作說明](leap_unity/README.md)，先啟動 Unity 接收端，再執行：

```powershell
python leap_unity\python\gesture_sender.py
```

預設傳送至 `127.0.0.1:8054`。必要的現代 Python API 原始碼隨專案提供，但仍需要原有 Ultraleap SDK、CFFI 繫結、追蹤服務與裝置。

本儲存庫提供 Unity 接收腳本，未包含完整 Unity 專案、場景或互動素材。腳本可分別移動左右手物件，目前傳送的是掌心位置，未實作完整手指骨架動畫。

## 驗證與限制

整理版已進行語法、原始模型架構比對及模擬 JSON／斷線清理檢查。尚未在原環境實際訓練、開啟攝影機或執行 Unity／Leap 裝置；詳見 [驗證說明](reference/驗證紀錄.md) 與 [環境說明](reference/套件與環境說明.md)。

手語模型仍是單手 63 維輸入，雙手追蹤屬於另一模組。資料切分修正會影響準確率，本次未重現或重新量測專題說明中的約 87%。目前沒有將 CNN-LSTM 辨識文字傳送至 Unity 場景的程式。
