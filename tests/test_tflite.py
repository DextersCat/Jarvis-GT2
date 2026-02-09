"""
Test with TensorFlow Lite instead of ONNX
"""
import numpy as np
import sounddevice as sd
import scipy.signal as signal
from openwakeword.model import Model

DEVICE = 17
WAKE_WORD = "hey_jarvis"

print("="*70)
print("TESTING WITH TFLITE (instead of ONNX)")
print("="*70)

print("\nLoading model with TensorFlow Lite...")
try:
    wake_model = Model(
        wakeword_models=[WAKE_WORD],
        inference_framework="tflite"  # Use TFLite instead of ONNX
    )
    print("✓ Model loaded with TFLite")
except Exception as e:
    print(f"✗ Failed: {e}")
    exit(1)

print("\n" + "="*70)
print("Say 'HEY JARVIS' - Recording for 5 seconds...")
print("="*70 + "\n")

input("Press ENTER, then say 'HEY JARVIS' multiple times...")

audio_48k = sd.rec(int(5 * 48000), samplerate=48000, device=DEVICE, channels=1, dtype='float32')
print("🎤 RECORDING - SAY 'HEY JARVIS'!")
sd.wait()
print("✓ Complete\n")

# Process
audio_mono = audio_48k.flatten()
audio_16k = signal.resample_poly(audio_mono, 1, 3)

print(f"Audio range: [{audio_mono.min():.3f}, {audio_mono.max():.3f}]")
print("\nAnalyzing...")
print("="*70)

max_score = 0
detections = []

num_chunks = len(audio_16k) // 1280

for i in range(num_chunks):
    chunk = audio_16k[i*1280:(i+1)*1280]
    chunk = np.ascontiguousarray(chunk, dtype=np.float32)
    
    predictions = wake_model.predict(chunk)
    score = predictions.get(WAKE_WORD, 0.0)
    
    if score > max_score:
        max_score = score
    
    if score > 0.01:
        time_sec = i * 1280 / 16000
        bar = "█" * int(score * 50)
        print(f"@ {time_sec:4.1f}s: {score:.4f} [{bar}]")
        detections.append((i, score))

print("="*70)
print(f"Max score: {max_score:.4f}")
print(f"Detections (>0.01): {len(detections)}")

if max_score > 0.3:
    print(f"\n✓ SUCCESS WITH TFLITE! Confidence: {max_score:.4f}")
    print("\n→ ONNX was the problem! Use inference_framework='tflite'")
elif max_score > 0.01:
    print(f"\n⚠ Weak detection: {max_score:.4f}")
    print("→ TFLite works better than ONNX, but still weak")
else:
    print(f"\n❌ Still no detection: {max_score:.4f}")
    print("→ Not an ONNX vs TFLite issue")
