# Quick Debugging Guide - OpenWakeWord Zero Confidence

## THE THREE MAIN PROBLEMS (and fixes)

### 1. Data Type Mismatch ❌ → ✅
```python
# WRONG - doesn't normalize
audio_16k.astype(np.float32)

# RIGHT - ensures proper format
audio_16k = np.ascontiguousarray(audio_16k, dtype=np.float32)
```

### 2. Channel Indexing ❌ → ✅
```python
# WRONG - crashes on mono
audio = indata[:, 0]

# RIGHT - handles both
audio = indata[:, 0] if len(indata.shape) == 2 else indata
```

### 3. Buffer Size ❌ → ✅
```python
# WRONG - assumes perfect division
audio_16k = resample_poly(audio, 1, 3)

# RIGHT - guarantees exact size
audio_16k = resample_poly(audio, 1, 3)
if len(audio_16k) != 1280:
    audio_16k = np.pad(audio_16k, (0, max(0, 1280-len(audio_16k))))[:1280]
```

---

## RUN THESE SCRIPTS IN ORDER

### 1️⃣ `synthetic_test.py` - Isolate hardware vs software
```bash
python synthetic_test.py
```
**What it does:** Tests model with generated audio, then compares to real mic
**Look for:** 
- ✅ Synthetic tests should show small non-zero numbers (0.0001-0.01)
- ❌ If all zeros → model file issue
- ❌ If mic scores are 0 but synthetic works → audio capture issue

---

### 2️⃣ `diagnostic_listener.py` - Deep analysis
```bash
python diagnostic_listener.py
```
**What it does:** Shows EVERYTHING - raw data, shapes, types, probabilities
**Look for:**
- `[INPUT RAW] Range:` should NOT be [0.0, 0.0]
- `[RESAMPLED] Shape:` must be exactly (1280,)
- `[MODEL OUTPUT]` should show your wake word as a key

**Outputs:**
- Every chunk shows full diagnostic info
- Speak "alexa" (or your wake word) to see confidence rise
- Press Ctrl+C when done to see summary

---

### 3️⃣ `fixed_listener.py` - Production use
```bash
python fixed_listener.py
```
**What it does:** Clean implementation with all fixes applied
**Features:**
- Direct Buffer mode (recommended) - perfect frame alignment
- Buffered mode (alternative) - for variable blocksizes
- Visual confidence bar
- Detection counter

---

## ONE-LINE FIXES FOR YOUR CODE

Replace lines 137-138 in `jarvis_main.py`:

**OLD:**
```python
audio_16k = signal.resample_poly(indata[:, 0], 1, 3)
preds = wake_model.predict(audio_16k.astype(np.float32))
```

**NEW:**
```python
# Safe channel extraction
audio_mono = indata[:, 0] if len(indata.shape) == 2 else indata

# Resample with size guarantee
audio_16k = signal.resample_poly(audio_mono, 1, 3)
if len(audio_16k) != 1280:
    audio_16k = np.pad(audio_16k, (0, max(0, 1280-len(audio_16k))))[:1280]

# Ensure proper format
audio_16k = np.ascontiguousarray(audio_16k, dtype=np.float32)

# Predict
preds = wake_model.predict(audio_16k)
```

---

## EXPECTED CONFIDENCE SCORES

| Situation | Score Range | Meaning |
|-----------|-------------|---------|
| Silence/noise | 0.0001 - 0.01 | Normal noise floor ✅ |
| Speaking (not wake word) | 0.01 - 0.1 | Detecting speech ✅ |
| Wake word mumbled | 0.2 - 0.4 | Weak detection 🟨 |
| Wake word clear | 0.5 - 0.95 | Strong detection ✅ |
| All zeros | 0.0 | DATA FORMAT ISSUE ❌ |

---

## QUICK DIAGNOSIS

### Symptom: All scores are 0.0
**Cause:** Data type or normalization issue
**Fix:** Apply the ONE-LINE FIXES above

### Symptom: Scores are 0.0001 but never rise
**Cause:** Microphone volume too low OR wrong device
**Fix:** 
- Increase mic volume in Windows Sound Settings
- Run `find_mics.py` to verify device index

### Symptom: High scores on silence
**Cause:** False positive threshold too low
**Fix:** Raise `WAKE_THRESHOLD` from 0.3 to 0.5

### Symptom: Script crashes "IndexError: too many indices"
**Cause:** Mono stream but code expects stereo
**Fix:** Use the channel indexing fix above

---

## WINDOWS-SPECIFIC CHECKS

1. **Microphone permissions:**
   - Settings → Privacy → Microphone → Allow desktop apps

2. **Exclusive mode (disable it):**
   - Sound Settings → Device Properties → Advanced
   - Uncheck "Allow applications to take exclusive control"

3. **Sample rate verification:**
   - Sound Settings → Device Properties → Advanced
   - Should show "48000 Hz" if your mic is locked

4. **Driver check:**
   - Device Manager → Audio inputs → Update driver
   - Some USB mics need ASIO drivers

---

## TESTING WORKFLOW

```bash
# Step 1: Quick test
python synthetic_test.py

# If synthetic works but mic doesn't:
python diagnostic_listener.py
# (Check output for zeros in INPUT RAW section)

# If diagnostic shows good data:
python fixed_listener.py
# (This is your production script)

# If nothing works:
# Read ANALYSIS.md for deep dive
```

---

## COMMON ERROR MESSAGES

### "Cannot set sample rate to 16000"
→ Your mic is locked at 48kHz (this is normal!)
→ Use the scripts which handle resampling automatically

### "IndexError: too many indices for array"
→ Mono channel issue
→ Fix: `audio[:, 0] if len(audio.shape)==2 else audio`

### "RuntimeError: Input array is not contiguous"
→ Memory layout issue
→ Fix: `np.ascontiguousarray(audio, dtype=np.float32)`

### All predictions are 0.0
→ Data format issue (most common!)
→ Run `synthetic_test.py` to verify model works
→ Then check mic audio format in `diagnostic_listener.py`

---

## FILES OVERVIEW

| File | Purpose | When to use |
|------|---------|-------------|
| `synthetic_test.py` | Test model + compare to mic | First step - isolate issue |
| `diagnostic_listener.py` | Deep analysis with all data | Debug data format issues |
| `fixed_listener.py` | Production implementation | After diagnosing - actual use |
| `ANALYSIS.md` | Full technical explanation | Deep dive / learning |
| `QUICKSTART.md` | This file | Quick reference |

---

Good luck! 🎯
