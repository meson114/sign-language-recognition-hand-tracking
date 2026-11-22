"""來源：E:/test_python3/gesture_sender.py。
保留 Leap Listener → 掌心座標 → JSON → TCP 傳 Unity 的做法。
補充：連線逾時與重連節流、關閉 socket、明確 left/right，以及選用的
原始握拳指令。先啟動 Unity，再執行此程式，Ctrl+C 結束。
注意：使用小寫 leap 的現代 API，不要混用舊版大寫 Leap.py / LeapPython.pyd。
"""
import sys
from pathlib import Path
# 使用這次一併整理的原始 Python API；不需要 pip 安裝這份原始碼。
# 它仍然依賴電腦原有的 Ultraleap SDK、CFFI 與追蹤服務。
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "vendor/leapc-python-api/src"))
try:
    import leap
except Exception as error:
    raise RuntimeError("無法載入原有 Ultraleap SDK/API，請依 leap_unity/README.md 檢查原環境與 SDK 路徑。") from error
import time
import socket
import json
import math

# --- 設定區 ---
UNITY_IP = '127.0.0.1'  # Unity 執行電腦的 IP (本機用 127.0.0.1)
UNITY_PORT = 8054       # 必須與 Unity 腳本中的 listenPort 一致
SEND_GESTURE_COMMANDS = False  # 原始握拳 SceneA 指令；此資料夾沒有 SceneA 場景，預設關閉。
TRIGGER_DISTANCE = 50   # 握拳判斷閾值 (mm)，小於此距離視為握拳

class GestureSenderListener(leap.Listener):
    def __init__(self):
        super().__init__()
        self.sock = None
        self.next_connect_time = 0.0
        self.connect_unity()
        self.last_gesture_time = 0

    def close_socket(self):
        if self.sock is not None:
            self.sock.close()
            self.sock = None

    def connect_unity(self):
        # 不要在每一個 Leap 追蹤回呼都反覆嘗試連線。
        if time.monotonic() < self.next_connect_time:
            return
        self.close_socket()
        try:
            self.sock = socket.create_connection((UNITY_IP, UNITY_PORT), timeout=1.0)
            self.sock.settimeout(0.2)
            print(f"Python 已連線到 Unity ({UNITY_IP}:{UNITY_PORT})")
        except OSError as error:
            self.next_connect_time = time.monotonic() + 2.0
            self.sock = None
            print(f"Unity 尚未連線，2 秒後再試：{error}")

    def send_json(self, data):
        """傳送 JSON 資料給 Unity (記得加換行符號)"""
        if self.sock is None:
            self.connect_unity() # 嘗試重連
            if self.sock is None: return

        try:
            message = json.dumps(data) + "\n" # Unity ReadLine 需要這個 \n
            self.sock.sendall(message.encode('utf-8'))
        except Exception as e:
            print(f"❌ 發送錯誤: {e}")
            self.close_socket()
            self.next_connect_time = time.monotonic() + 2.0

    def on_tracking_event(self, event):
        current_time = time.time()

        for hand in event.hands:
            # 1. --- 傳送手部座標 (Tracking) ---
            pos = [hand.palm.position.x, hand.palm.position.y, hand.palm.position.z]
            
            tracking_data = {
                "type": "tracking",
                "hand_type": "left" if hand.type == leap.HandType.Left else "right",
                "position": pos
            }
            self.send_json(tracking_data)

            # 2. --- 辨識手勢 (Command) ---
            # 簡單演算法：檢查「食指」指尖到「手掌中心」的距離
            # 如果您想做 "A動作"，我們可以定義 "握拳" 代表 A動作
            
            # 取得食指 (Index, id=1)
            if not SEND_GESTURE_COMMANDS or len(hand.digits) < 2:
                continue
            index_finger = hand.digits[1] 
            
            # 計算指尖 (Distal Joint) 到 手掌 (Palm) 的距離
            tip = index_finger.distal.next_joint
            palm = hand.palm.position
            
            distance = math.sqrt((tip.x - palm.x)**2 + (tip.y - palm.y)**2 + (tip.z - palm.z)**2)
            
            # 如果距離小於閾值 (代表手指縮起來了) 且 冷卻時間已過 (避免瘋狂切換)
            if distance < TRIGGER_DISTANCE and (current_time - self.last_gesture_time > 2.0):
                print(f"👊 偵測到動作 A (握拳)! 距離: {distance:.1f}mm -> 發送切換指令")
                
                command_data = {
                    "type": "command",
                    "content": "SceneA"
                }
                self.send_json(command_data)
                
                self.last_gesture_time = current_time

    def on_connection_event(self, event):
        print("✅ Leap Motion Service 連線成功")

    def on_device_event(self, event):
        print("✅ 裝置已連接")

def main():
    listener = GestureSenderListener()
    connection = leap.Connection()
    connection.add_listener(listener)

    print("程式執行中... 按 Ctrl+C 結束")
    try:
        with connection.open():
            connection.set_tracking_mode(leap.TrackingMode.Desktop)
            while True:
                time.sleep(1)
    except KeyboardInterrupt:
        print("已停止手部追蹤")
    finally:
        listener.close_socket()

if __name__ == "__main__":
    main()
