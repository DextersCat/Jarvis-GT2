"""
Debug what the model is actually receiving
"""
import numpy as np
import sounddevice as sd
import scipy.signal as signal
from openwakeword.model import Model

DEVICE = 17
WAKE_WORD = "hey_jarvis"

print("Loading model...")
wake_model = Model(wakeword_models=[WAKE_WORD], inference_framework="onnx")

print("\nRecording 1 second...")
audio_48k = sd.rec(48000, samplerate=48000, device=DEVICE, channels=1, dtype='float32')
sd.wait()

print("\nProcessing...")
audio_mono = audio_48k.flatten()
print(f"After flatten: shape={audio_mono.shape}, dtype={audio_mono.dtype}")
print(f"  Range: [{audio_mono.min():.6f}, {audio_mono.max():.6f}]")
print(f"  Mean: {audio_mono.mean():.6f}, Std: {audio_mono.std():.6f}")

# Resample
audio_16k = signal.resample_poly(audio_mono, 1, 3)
print(f"\nAfter resample: shape={audio_16k.shape}, dtype={audio_16k.dtype}")
print(f"  Range: [{audio_16k.min():.6f}, {audio_16k.max():.6f}]")

# Take first chunk
chunk = audio_16k[:1280]
print(f"\nFirst chunk: shape={chunk.shape}, dtype={chunk.dtype}")
print(f"  Range: [{chunk.min():.6f}, {chunk.max():.6f}]")
print(f"  Sample values [0:10]: {chunk[:10]}")

# Ensure float32
chunk = np.ascontiguousarray(chunk, dtype=np.float32)
print(f"\nAfter contiguous: shape={chunk.shape}, dtype={chunk.dtype}")
print(f"  is C-contiguous: {chunk.flags['C_CONTIGUOUS']}")
print(f"  Range: [{chunk.min():.6f}, {chunk.max():.6f}]")

# Test with model
print("\nFeeding to model...")
try:
    predictions = wake_model.predict(chunk)
    print(f"  ✓ Success!")
    print(f"  Predictions: {predictions}")
    score = predictions.get(WAKE_WORD, 0.0)
    print(f"  Score for '{WAKE_WORD}': {score}")
    
    # Check if ALL keys are zero
    all_zero = all(v == 0.0 for v in predictions.values())
    if all_zero:
        print("\n  ⚠ WARNING: ALL predictions are zero!")
        print("  This suggests the model is not processing the audio.")
except Exception as e:
    print(f"  ✗ Error: {e}")
    import traceback
    traceback.print_exc()

# Try with scaled audio (maybe it needs different normalization?)
print("\n" + "="*60)
print("Testing different normalizations...")
print("="*60)

for scale in [1.0, 10.0, 0.1, 100.0]:
    scaled = chunk * scale
    scaled = np.clip(scaled, -1.0, 1.0)  # Keep in valid range
    preds = wake_model.predict(scaled.astype(np.float32))
    score = preds.get(WAKE_WORD, 0.0)
    print(f"Scale {scale:5.1f}x: score = {score:.6f}")
