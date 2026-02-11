# Jarvis GT2 - OpenVINO Whisper Integration Plan

**Objective**: Offload Whisper transcription from the CPU to the Intel NPU (AI Boost) using OpenVINO for significantly lower latency and CPU usage.

**Methodology**: Research → Propose → Test → Verify

---

## 1. Research & Installation

### Dependencies:
1.  **Python**: 3.9, 3.10, or 3.11 (as required by OpenVINO).
2.  **Git**: Required for some dependency installations.
3.  **Microsoft C++ Build Tools**: May be required for compiling dependencies. Can be installed via Visual Studio Installer.
4.  **FFmpeg**: Required by Whisper for audio processing. Must be available in the system's PATH.

### Installation Steps:

1.  **Uninstall existing Whisper**: To avoid conflicts, the standard `openai-whisper` should be removed.
    ```bash
    pip uninstall openai-whisper
    ```

2.  **Install `openvino-whisper`**: The recommended package provides the necessary OpenVINO bindings.
    ```bash
    pip install openvino-whisper
    ```

3.  **Model Conversion**:
    OpenVINO requires the Whisper model to be converted to its Intermediate Representation (IR) format (`.xml` and `.bin` files). The `openvino-whisper` library handles this automatically on the first run. It will download the standard PyTorch model and convert it. The converted models will be cached, likely in `~/.cache/whisper-openvino/`.

4.  **Device Selection**:
    OpenVINO can target different hardware devices: `CPU`, `GPU` (integrated Intel Graphics), and `NPU`. The target device is specified when loading the model.

    -   `CPU`: Default, fallback device.
    -   `GPU`: For integrated Intel HD/Iris Xe Graphics.
    -   `NPU`: For the Intel AI Boost Neural Processing Unit.

    We will explicitly set the device to `NPU`.

---

## 2. Proposal (Code Implementation)

### File: `jarvis_main.py`

1.  **Modify `__init__` method**:
    -   Change the `whisper.load_model` call to specify the `NPU` device.
    -   Add a diagnostic check to log which device OpenVINO is actually using, as it may fall back to CPU/GPU if the NPU is unavailable.

    ```python
    # OLD
    # self.stt_model = whisper.load_model("base", device="cpu", download_root=None, in_memory=False)

    # NEW
    logger.info("Loading Whisper STT model via OpenVINO...")
    # Explicitly target the NPU. OpenVINO will fall back to GPU or CPU if NPU is not available.
    self.stt_model = whisper.load_model("base", device="NPU") 
    # The `device` attribute of the loaded model reports the actual device used.
    logger.info(f"✓ Whisper STT model offloaded to: {self.stt_model.device}")
    self.log(f"✓ STT offloaded to: {self.stt_model.device}")
    ```

2.  **Verify `transcribe` call**:
    The `transcribe` method signature for `openvino-whisper` is compatible with the original `openai-whisper`. No changes are needed in `listen_and_transcribe` or `continuous_listen_and_transcribe`.

---

## 3. Test & Verification

1.  **Run `jarvis_main.py`**:
    -   Check the startup logs for the "STT offloaded to: NPU" message.
    -   If it says `CPU` or `GPU`, it means the NPU was not detected or drivers are missing. This is a critical verification step.

2.  **Perform Voice Commands**:
    -   Test transcription accuracy. It should be identical to the original Whisper `base` model.
    -   Monitor CPU usage in Task Manager during transcription. It should be significantly lower than before. The "NPU" section in Task Manager (Performance tab) should show activity.