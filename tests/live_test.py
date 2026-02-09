"""
Live wake word test with Elgato Wave:3
Shows confidence scores in real-time
"""
import numpy as np
import sounddevice as sd
import scipy.signal as signal
from openwakeword.model import Model

DEVICE = 17  # Elgato Wave:3
WAKE_WORD = "hey_jarvis"
NATIVE_RATE = 48000
TARGET_RATE = 16000
CHUNK_48K = 3840
CHUNK_16K = 1280

print("="*70)
print(f"LIVE WAKE WORD TEST: '{WAKE_WORD}'")
print(f"Microphone: Elgato Wave:3 (device {DEVICE})")
print("="*70)

# Load model
print("\nLoading model...")
wake_model = Model(wakeword_models=[WAKE_WORD], inference_framework="onnx")
print("✓ Model loaded")

chunk_count = 0
high_scores = []

def callback(indata, frames, time_info, status):
    global chunk_count
    
    if status:
        print(f"Status: {status}")
    
    try:
        # Extract mono
        audio_mono = indata[:, 0] if len(indata.shape) == 2 else indata
        
        # Show input stats
        if chunk_count == 0:
            print(f"\nFirst chunk stats:")
            print(f"  Shape: {audio_mono.shape}")
            print(f"  Range: [{audio_mono.min():.3f}, {audio_mono.max():.3f}]")
            print(f"  dtype: {audio_mono.dtype}")
        
        # Resample to 16kHz
        audio_16k = signal.resample_poly(audio_mono, 1, 3)
        
        # Guarantee exact size
        if len(audio_16k) != CHUNK_16K:
            if len(audio_16k) < CHUNK_16K:
                audio_16k = np.pad(audio_16k, (0, CHUNK_16K - len(audio_16k)))
            else:
                audio_16k = audio_16k[:CHUNK_16K]
        
        # Ensure contiguous float32
        audio_16k = np.ascontiguousarray(audio_16k, dtype=np.float32)
        
        # Predict
        predictions = wake_model.predict(audio_16k)
        score = predictions.get(WAKE_WORD, 0.0)
        
        # Display
        chunk_count += 1
        
        if score > 0.01:
            bar = "█" * int(score * 50)
            print(f"\rChunk {chunk_count:4d} | Score: {score:.4f} [{bar:<50}]", end="", flush=True)
            high_scores.append(score)
        elif chunk_count % 10 == 0:
            print(f"\rChunk {chunk_count:4d} | Score: {score:.4f} [{'░'*50}]", end="", flush=True)
        
        # Detection
        if score > 0.5:
            print(f"\n\n{'🎯'*10}")
            print(f"DETECTED! Confidence: {score:.4f} ({score*100:.1f}%)")
            print(f"{'🎯'*10}\n")
            
    except Exception as e:
        print(f"\nError: {e}")
        import traceback
        traceback.print_exc()

print("\n" + "="*70)
print("🎤 LISTENING - Say 'Hey Jarvis'")
print("   Press Ctrl+C to stop")
print("="*70 + "\n")

try:
    with sd.InputStream(
        samplerate=NATIVE_RATE,
        device=DEVICE,
        channels=1,
        callback=callback,
        blocksize=CHUNK_48K,
        dtype='float32'
    ):
        while True:
            sd.sleep(1000)
            
except KeyboardInterrupt:
    print("\n\n" + "="*70)
    print("STOPPED")
    print("="*70)
    print(f"Total chunks: {chunk_count}")
    if high_scores:
        print(f"Scores > 0.01: {len(high_scores)}")
        print(f"Max score: {max(high_scores):.4f}")
        print(f"Detections (>0.5): {sum(1 for s in high_scores if s > 0.5)}")
    else:
        print("⚠ No significant scores detected")
        print("  Try speaking louder or closer to the microphone")
