# Leap Motion → Python → Unity

程式源自 `E:\test_python3`，整理後仍使用原本的小寫 `leap` API、Listener 回呼、JSON 與 TCP。

## 必要檔案

| 檔案 | 用途 |
|---|---|
| `python/gesture_sender.py` | 讀取 Leap 雙手掌心位置，以 TCP 傳送 JSON |
| `unity/PythonToUnityReceiver.cs` | Unity 接收座標並在主執行緒移動物件 |
| `vendor/leapc-python-api/` | 從原資料夾複製的現代 Python API，傳送程式會直接引用 |
| `vendor/leapc-cffi/` | 原有底層繫結原始碼，留供查閱與原環境維護 |

傳送程式會直接找到這份資料夾的 Python API 原始碼，不需要為了引用它重新 pip 安裝。它仍需要電腦原有可運作的 Ultraleap SDK、CFFI 繫結、追蹤服務與裝置；沒有這些原環境就無法憑原始碼取得追蹤資料。

所附 API 的 `__init__.py` 會在 `C:\Program Files\Ultraleap\LeapSDK` 找底層繫結。若你原本裝在其他地方，先設定原 SDK 位置，再執行：

```powershell
# 僅在原 SDK 裝在其他位置時設定，路徑需換成實際位置。
$env:LEAPSDK_INSTALL_LOCATION = '原本的 LeapSDK 完整路徑'
```

原 API README 指出 Gemini 5.17 起提供預建繫結；是否支援你原本的 Python 版本與架構，要以原 SDK 中的實際檔案為準。沒有在這次安裝、編譯或下載 SDK。不要把舊 `LeapPython.pyd` 當成現代 `leapc_cffi` 使用。

## 按順序操作

1. 使用你原本能運作的 Ultraleap 追蹤環境，接上裝置，先確認追蹤服務能看到雙手。
2. 開啟原 Unity 專案，把 `unity/PythonToUnityReceiver.cs` 放到 `Assets/Scripts/`。目前沒有找到完整原專案或場景。原始測試程式與舊 SDK 備份僅留於本機，未納入此儲存庫。
3. 接收腳本沿用原本的 `Newtonsoft.Json.Linq`。使用 Unity 專案原有的 Newtonsoft Json 套件；若專案沒有此套件，這支 C# 無法編譯。套件名稱為 `com.unity.nuget.newtonsoft-json`。本次未安裝套件。
4. 在場景建立空物件 `PythonReceiver`，掛上接收腳本。建立兩個可見物件（例如兩個 Sphere），分別指定到 Inspector 的 `Left Hand Object`、`Right Hand Object`。攝影機需看得到這兩個物件。這是掌心位置示意，不是完整手骨架動畫。
5. 確認 Inspector 的 `Listen Port` 是 `8054`。先按 Unity **Play**，Console 應顯示等待 Python 連線。
6. 在你原本的 Python 環境執行：

```powershell
# 在儲存庫根目錄執行
python leap_unity\python\gesture_sender.py
```

7. 移動雙手，確認左右兩個物件分別跟隨。按 `Ctrl+C` 停止 Python，再停止 Unity Play。

Python 預設連線到 `127.0.0.1:8054`，適用 Python 與 Unity 在同一台電腦。若分開兩台，在 `gesture_sender.py` 修改 `UNITY_IP` 為 Unity 電腦的實際 IP；兩端 port 需相同。

只想測單一物件時，可以不指定左右手欄位，改指定 `Leap Hand Object`；全部留空就移動掛載腳本的物件本身。雙手同時出現時建議明確指定左右手物件。

## 傳輸格式與整理修正

每個 JSON 都附上換行，讓 Unity 的 `ReadLine()` 能正確分辨 TCP 訊息：

```json
{"type":"tracking","hand_type":"left","position":[10.0,220.0,-30.0]}
```

座標沿用 Leap 掌心位置；Unity 沿用原程式的縮放 `/100`、Z 軸反向、位移偏移量及 Lerp 平滑。縮放與偏移已做成 Inspector 參數，這個 `/100` 是原場景的視覺比例，不能視為固定的毫米轉公尺換算。

補上了連線逾時、重連節流、斷線後接受新連線、結束時關閉 client，以及左右手分開更新。Unity 只保留每隻手最新座標，避免舊資料排隊造成延遲；Unity 物件操作集中在 `Update()`。

原傳送端的握拳 `SceneA` 指令仍保留，但 `SEND_GESTURE_COMMANDS = False`。沒有找到 `SceneA` 場景或對應場景切換接收器，接收端目前略過 command 封包。這份整理版沒有另造原本不存在的互動場景。

沒有手或斷線時，物件保留最後位置；目前未加入自動隱藏或完整手指骨架功能。兩隻手的掌心位置並不等於完整手部姿態重建。
