# Jarvis GT2 - NPU Integration Fallback Plan

**Date**: February 11, 2026
**Objective**: To revert the STT engine to a stable CPU-based mode to ensure application functionality, while deferring the NPU environment fix.

---

## Analysis

1.  **Environment Repair Failed**: The `pip install openvino-whisper` command failed, confirming a deep environmental incompatibility, likely due to an unsupported Python version. This means NPU offloading is not currently possible.
2.  **Missing Dependency**: The previous uninstall step removed `torch` and attempted to remove `openvino-whisper`. The environment is now missing a required STT library.
3.  **Path to Stability**: The highest priority is to return the application to a runnable state. We will install the standard `openai-whisper` package, which is universally compatible and will run on the CPU.

**Conclusion**: We will install the standard Whisper library and ensure the code explicitly uses the CPU. This guarantees startup. The task of creating a compatible Python environment for NPU offload will be tracked separately.

---

## Fallback Implementation

### Step 1: Install Standard `openai-whisper`
**Status**: ✅ **Completed**

The user has successfully installed the `openai-whisper` package, which provides the necessary `torch` dependency.
```powershell
pip install openai-whisper
```

### Step 2: Revert Code to CPU-based Whisper
The following change will be applied to `jarvis_main.py` to ensure the Whisper model loads on the CPU.
```python
# In jarvis_main.py, __init__ method:

logger.info("Loading Whisper STT model...")
# FALLBACK: Reverting to CPU due to NPU/OpenVINO environment issues.
self.stt_model = whisper.load_model("base", device="cpu")
logger.info(f"✓ Whisper STT model loaded on: {self.stt_model.device}")
```

### Step 3: Track Environment Fix
A new high-priority task has been added to `REFINEMENT_TODO.md` to investigate and create a compatible Python environment (e.g., using Python 3.11) to enable NPU offloading in the future.