# Packages and Environment

Please use a working Python interpreter and package environment that was already functional. This project does not include scripts to automatically download or install the environment.

| Module | Packages / Services Used |
| --- | --- |
| Video Extraction | OpenCV (`cv2`), MediaPipe (`mp.solutions.hands`), NumPy |
| Training | pandas, NumPy, scikit-learn, TensorFlow/Keras, Matplotlib, joblib |
| CSV Classification Testing | pandas, NumPy, scikit-learn, TensorFlow/Keras, joblib |
| Camera | OpenCV, MediaPipe, NumPy, TensorFlow/Keras, joblib; optional `pyttsx3` |
| Leap | Bundled modern `leap` API, legacy `leapc_cffi` / CFFI, Ultraleap SDK / tracking service and device |
| Unity | Unity runtime environment, Newtonsoft Json package |

`socket`, `json`, `threading`, `pathlib`, and `csv` are part of the Python standard library.

The original project did not preserve a complete package version lockfile, so there is no guarantee that arbitrary newer environments can load the legacy `.h5` model. If you encounter `mediapipe.solutions`, Keras loading, or DLL errors, first verify that you are using a previously working environment. No migration to newer APIs was performed in this pass.
