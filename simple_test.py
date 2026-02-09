"""
Step-by-step wake word test - shows everything happening
"""
import numpy as np
import sounddevice as sd
import scipy.signal as signal
from openwakeword.model import Model
import time

DEVICE = 17  # Elgato Wave:3
WAKE_WORD = "hey_jarvis"
NATIVE_RATE = 48000
TARGET_RATE = 16000
CHUNK_48K = 3840
CHUNK_16K = 1280
DURATION = 0.08  # 80ms chunks

print("="*70)
print("STEP-BY-STEP WAKE WORD TEST")
print("="*70)

# Load model
print("\n[1] Loading model...")
try:
    wake_model = Model(wakeword_models=[WAKE_WORD], inference_framework="onnx")
    print(f"    ✓ Model loaded for '{WAKE_WORD}'")
except Exception as e:
    print(f"    ✗ Failed: {e}")
    exit(1)

print("\n[2] Testing microphone...")
try:
    test_rec = sd.rec(4800, samplerate=48000, device=DEVICE, channels=1, dtype='float32')
    sd.wait()
    print(f"    ✓ Mic working - Range: [{test_rec.min():.3f}, {test_rec.max():.3f}]")
except Exception as e:
    print(f"    ✗ Mic failed: {e}")
    exit(1)

print("\n[3] Starting detection loop...")
print("    Say 'Hey Jarvis' now!")
print("="*70 + "\n")

try:
    chunk_num = 0
    while chunk_num < 200:  # ~16 seconds total
        # Record one chunk
        audio_48k = sd.rec(CHUNK_48K, samplerate=48000, device=DEVICE, channels=1, dtype='float32')
        sd.wait()
        
        # Extract mono
        audio_mono = audio_48k.flatten()
        
        # Show first chunk info
        if chunk_num == 0:
            print(f"First chunk captured:")
            print(f"  Shape: {audio_mono.shape}")
            print(f"  Range: [{audio_mono.min():.4f}, {audio_mono.max():.4f}]")
            print(f"  dtype: {audio_mono.dtype}\n")
        
        # Resample
        audio_16k = signal.resample_poly(audio_mono, 1, 3)
        
        # Ensure exact size
        if len(audio_16k) != CHUNK_16K:
            if len(audio_16k) < CHUNK_16K:
                audio_16k = np.pad(audio_16k, (0, CHUNK_16K - len(audio_16k)))
            else:
                audio_16k = audio_16k[:CHUNK_16K]
        
        # Ensure proper format
        audio_16k = np.ascontiguousarray(audio_16k, dtype=np.float32)
        
        # Predict
        predictions = wake_model.predict(audio_16k)
        score = predictions.get(WAKE_WORD, 0.0)
        
        chunk_num += 1
        
        # Show all scores (not just high ones)
        if score > 0.1:
            bar = "█" * int(score * 40)
            print(f"Chunk {chunk_num:3d}: {score:.4f} 📢 [{bar}]")
        elif score > 0.01:
            bar = "▓" * int(score * 40)
            print(f"Chunk {chunk_num:3d}: {score:.4f} 🔊 [{bar}]")
        elif chunk_num % 20 == 0:
            print(f"Chunk {chunk_num:3d}: {score:.4f} 🔇 [noise floor]")
        
        # Detection
        if score > 0.5:
            print("\n" + "🎯"*20)
            print(f"WAKE WORD DETECTED!")
            print(f"Confidence: {score:.4f} ({score*100:.1f}%)")
            print("🎯"*20 + "\n")
            
        time.sleep(0.01)  # Small delay between chunks
        
except KeyboardInterrupt:
    print("\n\n" + "="*70)
    print("STOPPED")
    print("="*70)
    print(f"Processed {chunk_num} chunks")

print("\nDone!")
