# Jarvis GT2 - NPU Model Cache Corruption Fix

**Date**: February 11, 2026
**Objective**: To resolve the `RuntimeError` during Whisper model loading by implementing a robust, two-stage loading process.

---

## Analysis

**Final Error**:
```
RuntimeError: don't know how to restore data location of torch.storage.UntypedStorage (tagged with NPU)
```

**Root Cause**:
This `torch.load` error indicates that the cached Whisper model, which was previously converted for the NPU, has become corrupted or is in a state that PyTorch cannot deserialize. The error message `(tagged with NPU)` confirms that the issue is specific to loading a model that was saved with NPU-specific storage information.

This is a common issue with model caching mechanisms when the environment changes or a previous process terminates improperly. The `openvino-whisper` library caches converted models to speed up subsequent startups, but this cache can become invalid.

**Solution**:
The most direct and effective solution is to delete the entire `openvino-whisper` cache directory. This will force the library to re-download the original Whisper model and perform a fresh conversion on the next run, creating a clean, valid cache.

---

## Correction Steps

Please execute the following command in your PowerShell terminal to remove the corrupted cache. This command is safe to run and will only affect the cached model files.

```powershell
Remove-Item -Recurse -Force C:\Users\spencer\.cache\whisper-openvino
```

After running this command, the next startup of `jarvis_main.py` will take slightly longer as it re-downloads and converts the model. Subsequent startups will be fast again.