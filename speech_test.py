"""
Record WHILE speaking - ensures we capture actual speech
"""
import numpy as np
import sounddevice as sd
import scipy.signal as signal
from openwakeword.model import Model
import sys

DEVICE = 17
WAKE_WORD = "hey_jarvis"

print("="*70)
print("SPEECH CAPTURE TEST")
print("="*70)

print("\nLoading model...")
wake_model = Model(wakeword_models=[WAKE_WORD], inference_framework="onnx")
print("✓ Model loaded")

print("\n" + "="*70)
print("START SAYING 'HEY JARVIS' REPEATEDLY - Recording for 5 seconds...")
print("="*70 + "\n")

input("Press ENTER when ready, then start speaking immediately...")

# Record 5 seconds
audio_48k = sd.rec(int(5 * 48000), samplerate=48000, device=DEVICE, channels=1, dtype='float32')
print("🎤 RECORDING NOW - SPEAK 'HEY JARVIS'!")
sd.wait()
print("✓ Recording complete\n")

# Process in chunks
audio_mono = audio_48k.flatten()
audio_16k = signal.resample_poly(audio_mono, 1, 3)

print(f"Total audio: {len(audio_16k)/16000:.1f} seconds")
print(f"Range: [{audio_mono.min():.3f}, {audio_mono.max():.3f}]")
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
    
    # Ensure proper format
    chunk = np.ascontiguousarray(chunk, dtype=np.float32)
    
    # Predict
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
print("RESULTS")
print("="*70)
print(f"Chunks processed: {num_chunks}")
print(f"Max score: {max_score:.4f} @ chunk {max_chunk} ({max_chunk*1280/16000:.1f}s)")
print(f"Scores > 0.01: {len(high_scores)}")

if max_score > 0.5:
    print(f"\n✓ DETECTED! Peak confidence: {max_score:.4f}")
elif max_score > 0.1:
    print(f"\n⚠ Weak detection - max {max_score:.4f}")
    print("  Try speaking louder or closer to mic")
elif max_score > 0.01:
    print(f"\n⚠ Very weak response - max {max_score:.4f}")
    print("  Model sees speech but not wake word")
else:
    print(f"\n❌ NO DETECTION - max {max_score:.4f}")
    print("  Possible issues:")
    print("  1. Model 'hey_jarvis' might not be working")
    print("  2. Audio quality issue")
    print("  3. Pronunciation doesn't match model expectations")
    print("\nTry: python -c \"from openwakeword.utils import download_models; download_models(['hey_jarvis'])\"")