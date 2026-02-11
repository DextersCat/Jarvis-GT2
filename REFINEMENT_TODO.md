# Jarvis GT2 - Refinements & Minor Issues

**Objective:** To track smaller bugs, UI tweaks, and quality-of-life improvements found during testing. This list is for items that do not require major architectural changes and can be addressed alongside the main refactoring plan.

---

## Bugs / Issues
- [ ] **[HIGH] Fix NPU Environment**: The `openvino-whisper` package is incompatible with the current Python environment. The system has been reverted to use CPU-based transcription. **Action**: Create a new virtual environment with a compatible Python version (e.g., 3.11) and reinstall `openvino-whisper` to re-enable NPU offloading.

---

## UI/UX Refinements

- [ ] *Example: The log text in the dashboard should use a monospace font for better alignment.*
- [ ] 

---

## New Feature Ideas (Small)

- [ ] *Example: Add a new voice command to clear the dashboard focus panel.*
- [ ] 

---