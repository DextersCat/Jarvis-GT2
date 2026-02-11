# Jarvis GT2 - Environment Repair Plan

**Date**: February 11, 2026
**Objective**: To resolve the `RuntimeError` during model loading by repairing the Python environment and ensuring library compatibility.

---

## Final Analysis

**Diagnostic Result**:
The `verify_npu.py` script has **successfully isolated the problem**. It failed with the exact same `RuntimeError` as the main application:
```
RuntimeError: don't know how to restore data location of torch.storage.UntypedStorage (tagged with AUTO)
```

**Conclusion**:
This definitively proves the issue is **not with the logic in `jarvis_main.py`**, but with the underlying software environment. The `openvino-whisper` library, its version of PyTorch, and the Intel NPU drivers are not communicating correctly on your system. The library is failing to properly register the "NPU" or "AUTO" device types with PyTorch's model loading system.

**Path to Resolution**:
We must repair the environment. The most robust way to fix such deep-seated library conflicts is to perform a clean re-installation of the core components. This forces `pip` to resolve the dependency tree correctly and ensures that compatible versions of `openvino-whisper`, `openvino`, and `torch` are installed.

---

## Environment Repair Steps

Please execute the following commands in your PowerShell terminal while your virtual environment (`.venv`) is active.

### Step 1: Uninstall Core AI/ML Libraries
**Status**: ✅ **Completed**

The user has executed the uninstall command. The output confirmed that `torch` was uninstalled, but `openvino-whisper` and `openvino` were not found by `pip`. This indicates an inconsistent environment state, reinforcing the need for a clean installation.

```powershell
pip uninstall openvino-whisper torch openvino -y
```

### Step 2: Reinstall `openvino-whisper`
This command will reinstall the main library. Crucially, it will also automatically pull in the specific versions of `openvino` and `torch` that it has been tested with, resolving any version mismatches.
```powershell
pip install openvino-whisper
```

---

## Next Steps

After completing these two steps, the environment should be repaired. We can then re-run the `verify_npu.py` script. A successful run of that script will confirm the fix, and `jarvis_main.py` should then start correctly.