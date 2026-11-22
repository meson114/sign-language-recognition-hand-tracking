"""Source: E:/test_python3/gesture_sender.py.
Preserves the Leap Listener -> palm coordinates -> JSON -> TCP to Unity workflow.
Additions: connection timeouts and reconnect throttling, closing sockets, explicit left/right labels, and an optional
original fist command. Start Unity first, then run this script; press Ctrl+C to exit.
Note: Use the modern lowercase `leap` API; do not mix with the legacy uppercase Leap.py / LeapPython.pyd.
"""
import sys
from pathlib import Path
# Use the original Python API source organized alongside this repo; no pip install needed for this source.
# It still depends on the machine's existing Ultraleap SDK, CFFI, and tracking service.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "vendor/leapc-python-api/src"))
try:
    import leap
except Exception as error:
    raise RuntimeError("Unable to load the existing Ultraleap SDK/API; check the original environment and SDK path according to leap_unity/README.md.") from error
import time
import socket
import json
import math

# --- Configuration ---
UNITY_IP = '127.0.0.1'  # IP address of the machine running Unity (use 127.0.0.1 for local machine)
UNITY_PORT = 8054       # Must match listenPort in the Unity script
SEND_GESTURE_COMMANDS = False  # Original fist SceneA command; no SceneA scene in this folder, disabled by default.
TRIGGER_DISTANCE = 50   # Fist detection threshold (mm); distances below this are treated as a fist

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
        # Do not repeatedly attempt to connect on every Leap tracking callback.
        if time.monotonic() < self.next_connect_time:
            return
        self.close_socket()
        try:
            self.sock = socket.create_connection((UNITY_IP, UNITY_PORT), timeout=1.0)
            self.sock.settimeout(0.2)
            print(f"Python connected to Unity ({UNITY_IP}:{UNITY_PORT})")
        except OSError as error:
            self.next_connect_time = time.monotonic() + 2.0
            self.sock = None
            print(f"Unity not connected yet, retrying in 2 seconds: {error}")

    def send_json(self, data):
        """Send JSON data to Unity (remember to append a newline character)"""
        if self.sock is None:
            self.connect_unity() # Attempt to reconnect
            if self.sock is None: return

        try:
            message = json.dumps(data) + "\n" # Unity ReadLine requires this \n
            self.sock.sendall(message.encode('utf-8'))
        except Exception as e:
            print(f"❌ Send error: {e}")
            self.close_socket()
            self.next_connect_time = time.monotonic() + 2.0

    def on_tracking_event(self, event):
        current_time = time.time()

        for hand in event.hands:
            # 1. --- Send hand coordinates (Tracking) ---
            pos = [hand.palm.position.x, hand.palm.position.y, hand.palm.position.z]
            
            tracking_data = {
                "type": "tracking",
                "hand_type": "left" if hand.type == leap.HandType.Left else "right",
                "position": pos
            }
            self.send_json(tracking_data)

            # 2. --- Gesture recognition (Command) ---
            # Simple algorithm: check the distance from the index fingertip to the palm center
            # If you want to implement "Action A", we can define a "fist" to represent Action A

            # Get the index finger (Index, id=1)
            if not SEND_GESTURE_COMMANDS or len(hand.digits) < 2:
                continue
            index_finger = hand.digits[1] 
            
            # Calculate the distance from the fingertip (Distal Joint) to the palm (Palm)
            tip = index_finger.distal.next_joint
            palm = hand.palm.position
            
            distance = math.sqrt((tip.x - palm.x)**2 + (tip.y - palm.y)**2 + (tip.z - palm.z)**2)
            
            # If the distance is below the threshold (indicating the finger is curled) and the cooldown has elapsed (to avoid rapid toggling)
            if distance < TRIGGER_DISTANCE and (current_time - self.last_gesture_time > 2.0):
                print(f"👊 Detected Action A (fist)! Distance: {distance:.1f}mm -> Sending switch command")
                
                command_data = {
                    "type": "command",
                    "content": "SceneA"
                }
                self.send_json(command_data)
                
                self.last_gesture_time = current_time

    def on_connection_event(self, event):
        print("✅ Leap Motion Service connected")

    def on_device_event(self, event):
        print("✅ Device connected")

def main():
    listener = GestureSenderListener()
    connection = leap.Connection()
    connection.add_listener(listener)

    print("Program running... Press Ctrl+C to exit")
    try:
        with connection.open():
            connection.set_tracking_mode(leap.TrackingMode.Desktop)
            while True:
                time.sleep(1)
    except KeyboardInterrupt:
        print("Hand tracking stopped")
    finally:
        listener.close_socket()

if __name__ == "__main__":
    main()
