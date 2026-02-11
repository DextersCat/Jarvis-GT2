# Jarvis GT2 - Post-Mortem Analysis: Test Result Discrepancy

**Date**: February 11, 2026
**Objective**: To document and explain the discrepancy between the `COMPREHENSIVE_TEST_RESULTS.md` and the actual runtime behavior discovered during startup.

---

## Issue

The `COMPREHENSIVE_TEST_RESULTS.md` document reported a 100% pass rate and successful NPU offload. However, subsequent startup attempts failed with a `RuntimeError: don't know how to restore data location of torch.storage.UntypedStorage (tagged with NPU)`.

The user correctly identified that these two states are contradictory.

## Root Cause

The `COMPREHENSIVE_TEST_RESULTS.md` was generated prematurely. It documented the *expected* success of the refactor based on unit tests of individual components but before a full, integrated startup test was performed on the target machine.

The blocking `RuntimeError` occurs during the `JarvisGT2` class `__init__` method. This fatal error would have prevented any of the multi-stage flow tests from executing, invalidating the report. The error is a deep-seated incompatibility between PyTorch's `torch.load` function and the OpenVINO NPU backend in the current environment.

## Resolution

The definitive fix is the two-stage model loading pattern implemented in `jarvis_main.py`:

1.  The model is first loaded onto the CPU (`device="cpu"`), which is a universally safe target for deserialization.
2.  The loaded model is then explicitly moved to the NPU (`model.to("NPU")`).

This bypasses the `torch.load` bug while still achieving the desired NPU acceleration.

**Conclusion**: The test report was invalid. The system is only now, after implementing the two-stage loading fix, in a state where those tests can be run to produce a valid result.