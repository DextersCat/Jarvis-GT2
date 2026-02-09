# OpenWakeWord Zero Confidence Analysis
## Windows 48kHz Microphone Issues

---

## ROOT CAUSES IDENTIFIED

### 1. **Data Type Mismatches** ⚠️ CRITICAL
**Problem:** OpenWakeWord's ONNX model expects specific float32 input
- Windows audio drivers often return `int16` PCM data
- `sounddevice` returns `float32` BUT range must be [-1.0, 1.0]
- If you convert int16 → float32 without normalization, the model sees values like 15000.0 instead of 0.5
- This causes the neural network to output garbage (zeros)

**Your Code Issue:**
```python
audio_16k = signal.resample_poly(indata[:, 0], 1, 3)
preds = wake_model.predict(audio_16k.astype(np.float32))
```
The `.astype()` does NOT normalize! It just changes the type label.

**Fix:**
```python
# Ensure normalized float32
audio_float32 = audio_16k.astype(np.float32)
# If it's not already normalized, do this:
if audio_float32.max() > 1.0:
    audio_float32 = audio_float32 / 32768.0  # int16 → float32 conversion
```

---

### 2. **Channel Indexing Error** 🔧
**Problem:** `indata[:, 0]` assumes 2D array (stereo), but mono streams are 1D

**Your Code:**
```python
audio_16k = signal.resample_poly(indata[:, 0], 1, 3)
```

**What happens:** If `indata.shape = (3840,)` instead of `(3840, 1)`, this crashes or returns wrong data

**Fix:**
```python
if len(indata.shape) == 2:
    audio_mono = indata[:, 0]
else:
    audio_mono = indata  # Already mono
```

---

### 3. **Buffer Alignment Issues** 📦
**Problem:** `resample_poly` can produce slight size variations due to:
- Edge effects in the polyphase filter
- Floating-point rounding in the resampling calculation

**Your blocksize:** `WAKE_CHUNK * 3 = 3840`
- Theoretically: 3840 / 3 = 1280 ✓
- In practice: `resample_poly(3840, 1, 3)` might return 1279 or 1281 samples

**Why this breaks openWakeWord:**
The model is compiled to accept EXACTLY 1280 samples (80ms at 16kHz). Feeding 1279 causes:
- ONNX runtime error OR
- Model pads with zeros → detection fails

**Fix:**
```python
audio_16k = signal.resample_poly(audio_mono, 1, 3)

# Guarantee exact size
if len(audio_16k) != 1280:
    if len(audio_16k) < 1280:
        audio_16k = np.pad(audio_16k, (0, 1280 - len(audio_16k)))
    else:
        audio_16k = audio_16k[:1280]
```

---

### 4. **Memory Contiguity** 🧠
**Problem:** NumPy operations can create non-contiguous arrays
- Slicing (`[:, 0]`) creates a view, not a copy
- `resample_poly` might return non-contiguous memory
- ONNX runtime requires contiguous C-ordered arrays

**Symptom:** Model returns zeros even with correct data

**Fix:**
```python
audio_16k = np.ascontiguousarray(audio_16k, dtype=np.float32)
```

---

### 5. **Silent Failure on Windows** 🪟
**Windows-specific issue:** DirectSound/WASAPI can:
- Lock sample rates (48kHz only)
- Return zeros if exclusive mode fails
- Provide data but with wrong endianness

**How to detect:**
```python
print(f"Min: {audio_16k.min()}, Max: {audio_16k.max()}, Mean: {audio_16k.mean()}")
```
If all values are 0.0 → microphone not providing data
If all values are ±1.0 → clipping issue

---

## THE ZERO CONFIDENCE DEBUGGING CHECKLIST

Run these checks IN ORDER:

### ✅ Step 1: Verify Raw Audio
```python
print(f"Shape: {indata.shape}, dtype: {indata.dtype}")
print(f"Range: [{indata.min()}, {indata.max()}]")
print(f"Non-zero samples: {np.count_nonzero(indata)}")
```
**Expected:** Shape (3840, 1) or (3840,), dtype float32, range [-0.5, 0.5]
**If you see:** All zeros → mic not working, check device index

### ✅ Step 2: Check Resampling Output
```python
audio_16k = signal.resample_poly(audio_mono, 1, 3)
print(f"Resampled length: {len(audio_16k)} (expected 1280)")
print(f"Type: {audio_16k.dtype}, Range: [{audio_16k.min()}, {audio_16k.max()}]")
```
**Expected:** Length exactly 1280, dtype float32/float64, same range as input
**If wrong length:** Use padding/trimming fix above

### ✅ Step 3: Inspect Model Output
```python
predictions = wake_model.predict(audio_16k.astype(np.float32))
print(f"Full predictions dict: {predictions}")
```
**Expected:** Something like `{'alexa': 0.00123, 'hey_jarvis': 0.00045}`
**If all zeros:** Data type or normalization issue
**If no key 'alexa':** Wrong model file or wake word name

### ✅ Step 4: Test with Known Audio
```python
# Generate 1280 samples of 400 Hz tone
test_signal = np.sin(2 * np.pi * 400 * np.arange(1280) / 16000).astype(np.float32)
predictions = wake_model.predict(test_signal)
print(predictions)
```
**Expected:** Non-zero predictions (even if wrong word)
**If still zeros:** Model file corrupted or wrong framework

---

## COMMON MISTAKES (DON'T DO THIS) ❌

### ❌ Manual Decimation
```python
# BAD: Throws away information
audio_16k = audio_48k[::3]
```
This is like resizing an image by deleting pixels. Use `resample_poly` - it applies proper anti-aliasing.

### ❌ Accumulating Drift
```python
# BAD: Buffer grows unbounded
self.buffer = np.append(self.buffer, new_audio)
```
Every `append` reallocates memory. Use fixed-size ring buffer or consume chunks immediately.

### ❌ Wrong Normalization
```python
# BAD: Scales to [0, 1] instead of [-1, 1]
audio_normalized = (audio - audio.min()) / (audio.max() - audio.min())
```
Audio should be bipolar. Use: `audio / 32768.0` for int16.

### ❌ Assuming Stereo
```python
# BAD: Crashes on mono streams
left_channel = audio[:, 0]
```
Always check shape first.

---

## RECOMMENDED TESTING SEQUENCE

1. **Run `diagnostic_listener.py`** - Outputs everything
   - If you see zeros in [INPUT RAW], mic isn't working
   - If you see zeros in [MODEL OUTPUT], data format issue
   - If you see 0.00001-0.001 range, it's "thinking" (good sign!)

2. **Try `fixed_listener.py`** - Production implementation
   - Mode 1 (Direct Buffer) is most efficient
   - Mode 2 (Buffered) if you have variable blocksizes

3. **If still failing, override sample rate:**
   ```python
   # Force 16kHz directly (if your mic supports it)
   with sd.InputStream(samplerate=16000, device=1, channels=1):
       # No resampling needed!
       predictions = wake_model.predict(indata[:, 0])
   ```

---

## EXPECTED BEHAVIOR

**Idle/Silence:** Confidence 0.0001 - 0.01 (noise floor)
**Speaking unrelated:** 0.01 - 0.1
**Wake word said clearly:** 0.5 - 0.95
**Wake word mumbled:** 0.2 - 0.4

If you're getting **exactly 0.0** every time, it's a data format issue, NOT a detection issue.

---

## YOUR SPECIFIC BUG

In your `jarvis_main.py` line 137-138:
```python
audio_16k = signal.resample_poly(indata[:, 0], 1, 3)
preds = wake_model.predict(audio_16k.astype(np.float32))
```

**Two issues:**
1. `indata[:, 0]` will fail if sounddevice returns mono (1D array)
2. No verification that `audio_16k` is exactly 1280 samples

**Fixed version:**
```python
# Safe channel extraction
audio_mono = indata[:, 0] if len(indata.shape) == 2 else indata

# Resample
audio_16k = signal.resample_poly(audio_mono, 1, 3)

# Guarantee exact size
if len(audio_16k) != 1280:
    audio_16k = np.pad(audio_16k, (0, max(0, 1280 - len(audio_16k))))[:1280]

# Ensure contiguous float32
audio_16k = np.ascontiguousarray(audio_16k, dtype=np.float32)

# Predict
preds = wake_model.predict(audio_16k)
```

---

## WINDOWS-SPECIFIC TIPS

1. **Check exclusive mode:** Windows Sound Settings → Device → Advanced
   - Disable "Allow applications to take exclusive control"
   
2. **Sample rate lock:** If your mic ONLY supports 48kHz, resampling is mandatory
   - Use `fixed_listener.py` which handles this correctly
   
3. **WASAPI issues:** If `sounddevice` fails, try:
   ```python
   sd.default.device = 1  # Set before creating stream
   ```

4. **Driver conflicts:** Some USB mics/interfaces require ASIO drivers on Windows
   - Standard DirectSound might produce zeros

---

## NEXT STEPS

1. Run `diagnostic_listener.py` and save the output
2. Look for these lines:
   - `[INPUT RAW] Range:` - Should NOT be [0.0, 0.0]
   - `[RESAMPLED] Shape:` - Must be (1280,)
   - `[MODEL OUTPUT] Raw predictions:` - Should have your wake word as key
   
3. If all looks good but confidence is still 0.0:
   - Test with `python -m openwakeword.test` (official test)
   - Verify model file: `jarvis-high.onnx` might be for TTS, not wake word
   - Check you downloaded the alexa model: `openwakeword download-model --name alexa`

---

## SUMMARY: THE THREE CRITICAL FIXES

```python
# 1. Safe channel extraction
audio_mono = indata.flatten() if len(indata.shape) == 2 else indata

# 2. Exact size guarantee
audio_16k = signal.resample_poly(audio_mono, 1, 3)
audio_16k = np.ascontiguousarray(audio_16k[:1280] if len(audio_16k) >= 1280 
                                  else np.pad(audio_16k, (0, 1280-len(audio_16k))),
                                  dtype=np.float32)

# 3. Model prediction
predictions = wake_model.predict(audio_16k)  # Already float32, no .astype() needed
```

This guarantees:
- ✅ No shape mismatch
- ✅ Exact 1280 samples
- ✅ Contiguous float32 array
- ✅ Compatible with ONNX runtime on Windows

Good luck! 🎯
