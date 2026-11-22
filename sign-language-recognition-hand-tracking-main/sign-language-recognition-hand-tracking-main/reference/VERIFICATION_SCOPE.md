# Verification Scope

47 checks were completed during local organization, including:
- Python syntax checks for the five main sign language programs, shared configuration, and the Leap sender.
- Verification that `build_model` in `02_train.py` has an AST identical to the original `train.py`.
- Verification that the wrist-centering formulas in feature extraction, video testing, and camera recognition match the original version.
- Verification that the local raw backup matches the source files, and that the provided model / scaler match the original files.
- Checks using a simulated SDK / socket for left/right hand JSON, newline delimiters, coordinates, connection cleanup, and disconnect retry throttling.

Raw backups and detailed local check outputs are not included in this streamlined repository.

Loading TensorFlow / MediaPipe models, retraining, opening the camera, building Unity, or testing Leap hardware in the actual environment has not yet been performed. Therefore, these checks cannot be treated as having completed end-to-end execution in the real environment, and accuracy was not re-measured in this pass.
