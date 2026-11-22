# Leap Motion → Python → Unity

The code originates from `E:\test_python3` and, after organization, still uses the original lowercase `leap` API, Listener callbacks, JSON, and TCP.

## Required Files

| File | Purpose |
|---|---|
| `python/gesture_sender.py` | Reads both hands' palm positions from Leap and sends JSON over TCP |
| `unity/PythonToUnityReceiver.cs` | Receives coordinates in Unity and moves objects on the main thread |
| `vendor/leapc-python-api/` | Modern Python API copied from the original folder, imported directly by the sender script |
| `vendor/leapc-cffi/` | Original low-level binding source code, kept for reference and original environment maintenance |

The sender script directly locates the Python API source code in this folder, so you do not need to reinstall it via `pip` just to import it. It still requires your machine's existing working Ultraleap SDK, CFFI bindings, tracking service, and device; without that original environment, tracking data cannot be obtained from the source code alone.

The bundled API's `__init__.py` looks for low-level bindings in `C:\Program Files\Ultraleap\LeapSDK`. If your original installation is elsewhere, set the original SDK path first, then run:

```powershell
# Set only if the original SDK was installed elsewhere; replace with the actual path.
$env:LEAPSDK_INSTALL_LOCATION = 'full path to your original LeapSDK'

The original API README notes that prebuilt bindings are provided starting with Gemini 5.17; whether your original Python version and architecture are supported depends on the actual files in your original SDK. No SDK was installed, compiled, or downloaded in this pass. Do not use the legacy LeapPython.pyd as the modern leapc_cffi.

Step-by-Step Instructions
1. Using your previously working Ultraleap tracking environment, connect the device and first verify that the tracking service can see both hands.

2. Open the original Unity project and place unity/PythonToUnityReceiver.cs into Assets/Scripts/. The complete original project or scenes were not found. Original test scripts and legacy SDK backups remain only on the local machine and are not included in this repository.

3. The receiver script continues to use the original Newtonsoft.Json.Linq. Use the Unity project's existing Newtonsoft Json package; if the project does not have this package, the C# script will not compile. The package name is com.unity.nuget.newtonsoft-json. No packages were installed in this pass.

4. Create an empty GameObject named PythonReceiver in the scene and attach the receiver script. Create two visible objects (for example, two Spheres) and assign them to Left Hand Object and Right Hand Object in the Inspector. Make sure the camera can see both objects. This is a palm-position visualization, not a full hand-skeleton animation.

5. Confirm that Listen Port in the Inspector is 8054. Press Play in Unity first; the Console should indicate it is waiting for a Python connection.

6. Run in your original Python environment:
# Run from the repository root
python leap_unity\python\gesture_sender.py

7. Move both hands and verify that the left and right objects follow separately. Press Ctrl+C to stop Python, then stop Unity Play.

By default, Python connects to 127.0.0.1:8054, which works when Python and Unity run on the same machine. If they run on two separate machines, update UNITY_IP in gesture_sender.py to the Unity machine's actual IP address, and ensure both sides use the same port.

If you only want to test a single object, you can leave the left/right hand fields unassigned and specify Leap Hand Object instead; leaving all of them blank moves the object to which the script is attached. When both hands appear at the same time, explicitly assigning the left and right hand objects is recommended.

Wire Format and Organization Fixes
Each JSON message ends with a newline so Unity's ReadLine() can distinguish TCP messages properly:
{"type":"tracking","hand_type":"left","position":[10.0,220.0,-30.0]}
Coordinates follow the Leap palm position; Unity retains the original script's /100 scaling, Z-axis inversion, position offset, and Lerp smoothing. Scale and offset are exposed as Inspector parameters; this /100 is the visual scale of the original scene and should not be treated as a fixed millimeter-to-meter conversion.

Added connection timeouts, reconnect throttling, accepting new connections after disconnects, closing the client on exit, and separate updates for left and right hands. Unity keeps only the latest coordinate per hand to prevent stale data from queuing up and causing lag; Unity object operations are consolidated in Update().

The fist SceneA command from the original sender is preserved, but SEND_GESTURE_COMMANDS = False. No SceneA scene or corresponding scene-switching receiver was found, so the receiver currently ignores command packets. This organized version does not fabricate interactive scenes that did not exist originally.

When no hands are detected or the connection drops, objects stay at their last position; auto-hiding and full finger-skeleton reconstruction have not been added. Two hands' palm positions are not equivalent to full hand-pose reconstruction.
