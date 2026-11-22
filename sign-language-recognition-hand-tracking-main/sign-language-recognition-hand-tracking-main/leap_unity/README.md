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
