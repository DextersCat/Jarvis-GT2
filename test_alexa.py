"""
Test with ALEXA model to verify the system works
"""
import numpy as np
import sounddevice as sd
import scipy.signal as signal
from openwakeword.model import Model

DEVICE = 17
WAKE_WORD = "alexa"

print("="*70)
print("TESTING WITH 'ALEXA' MODEL")
print("="*70)

print("\nLoading model...")
wake_model = Model(wakeword_models=[WAKE_WORD], inference_framework="onnx")
print("✓ Model loaded")

print("\n" + "="*70)
print("Say 'ALEXA' repeatedly - Recording for 5 seconds...")
print("="*70 + "\n")

input("Press ENTER, then say 'ALEXA' multiple times...")

audio_48k = sd.rec(int(5 * 48000), samplerate=48000, device=DEVICE, channels=1, dtype='float32')
print("🎤 RECORDING NOW - SAY 'ALEXA'!")
sd.wait()
print("✓ Recording complete\n")

# Process
audio_mono = audio_48k.flatten()
audio_16k = signal.resample_poly(audio_mono, 1, 3)

print(f"Audio range: [{audio_mono.min():.3f}, {audio_mono.max():.3f}]")
print("\nProcessing chunks...")
print("="*70)

max_score = 0
max_chunk = 0
high_scores = []

num_chunks = len(audio_16k) // 1280

for i in range(num_chunks):
    start = i * 1280
    end = start + 1280
    chunk = audio_16k[start:end]
    chunk = np.ascontiguousarray(chunk, dtype=np.float32)
    
    predictions = wake_model.predict(chunk)
    score = predictions.get(WAKE_WORD, 0.0)
    
    if score > max_score:
        max_score = score
        max_chunk = i
    
    if score > 0.01:
        high_scores.append((i, score))
        bar = "█" * int(score * 50)
        time_sec = i * 1280 / 16000
        print(f"Chunk {i:3d} @ {time_sec:4.1f}s: {score:.4f} [{bar}]")

print("\n" + "="*70)
print("RESULTS WITH ALEXA MODEL")
print("="*70)
print(f"Max score: {max_score:.4f}")
print(f"High scores (>0.01): {len(high_scores)}")

if max_score > 0.1:
    print(f"\n✓ ALEXA MODEL WORKS! Detection: {max_score:.4f}")
    print("\n→ This means the system works, but 'hey_jarvis' model may be broken")
    print("→ Let's try re-downloading hey_jarvis...")
else:
    print(f"\n❌ Even ALEXA doesn't work (max {max_score:.4f})")
    print("→ This suggests a fundamental issue with openWakeWord setup")
