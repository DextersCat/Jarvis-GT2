"""
SYNTHETIC AUDIO TEST
Tests openWakeWord model with generated audio to isolate hardware issues
"""
import numpy as np
from openwakeword.model import Model
import sounddevice as sd
import scipy.signal as signal

WAKE_WORD = "hey_jarvis"
TARGET_RATE = 16000
CHUNK_SIZE = 1280

print("="*70)
print("SYNTHETIC AUDIO TEST - Hardware vs Software Isolation")
print("="*70)

# Load model
print(f"\n[1] Loading model for '{WAKE_WORD}'...")
try:
    wake_model = Model(wakeword_models=[WAKE_WORD], inference_framework="onnx")
    print("✓ Model loaded successfully")
except Exception as e:
    print(f"✗ Failed to load model: {e}")
    exit(1)

print(f"\n[2] Testing model with synthetic signals...")
print("-"*70)

# Test 1: Silence
print("\n[Test 1] Pure silence (all zeros)")
silence = np.zeros(CHUNK_SIZE, dtype=np.float32)
predictions = wake_model.predict(silence)
score = predictions.get(WAKE_WORD, 0.0)
print(f"  Result: {score:.6f}")
print(f"  Expected: ~0.0 (very low)")
if score > 0.1:
    print("  ⚠ WARNING: High confidence on silence! Model might be broken.")

# Test 2: White noise
print("\n[Test 2] White noise")
noise = np.random.randn(CHUNK_SIZE).astype(np.float32) * 0.1
predictions = wake_model.predict(noise)
score = predictions.get(WAKE_WORD, 0.0)
print(f"  Result: {score:.6f}")
print(f"  Expected: 0.0 - 0.05 (noise floor)")

# Test 3: Sine wave (400 Hz tone)
print("\n[Test 3] Pure tone (400 Hz)")
t = np.arange(CHUNK_SIZE) / TARGET_RATE
tone = (np.sin(2 * np.pi * 400 * t)).astype(np.float32)
predictions = wake_model.predict(tone)
score = predictions.get(WAKE_WORD, 0.0)
print(f"  Result: {score:.6f}")
print(f"  Expected: 0.0 - 0.02 (not speech)")

# Test 4: Chirp (speech-like frequency sweep)
print("\n[Test 4] Chirp (speech-like frequencies 100-3000 Hz)")
chirp = signal.chirp(t, f0=100, f1=3000, t1=t[-1], method='linear').astype(np.float32)
predictions = wake_model.predict(chirp)
score = predictions.get(WAKE_WORD, 0.0)
print(f"  Result: {score:.6f}")
print(f"  Expected: 0.01 - 0.15 (speech-like but not wake word)")

# Test 5: Extreme values (test clipping behavior)
print("\n[Test 5] Extreme values (near clipping)")
extreme = np.random.randn(CHUNK_SIZE).astype(np.float32)
extreme = np.clip(extreme, -0.99, 0.99)
predictions = wake_model.predict(extreme)
score = predictions.get(WAKE_WORD, 0.0)
print(f"  Result: {score:.6f}")

# Test 6: Wrong data type (common mistake)
print("\n[Test 6] Wrong data type (int16 not converted)")
int_audio = (np.random.randn(CHUNK_SIZE) * 10000).astype(np.int16)
try:
    predictions = wake_model.predict(int_audio)
    score = predictions.get(WAKE_WORD, 0.0)
    print(f"  Result: {score:.6f}")
    print("  ⚠ Model accepted int16! This should fail or give zeros.")
except Exception as e:
    print(f"  ✓ Correctly rejected: {e}")

# Test 7: Wrong size
print("\n[Test 7] Wrong buffer size (1000 instead of 1280)")
wrong_size = np.random.randn(1000).astype(np.float32)
try:
    predictions = wake_model.predict(wrong_size)
    score = predictions.get(WAKE_WORD, 0.0)
    print(f"  Result: {score:.6f}")
    print("  ⚠ Model accepted wrong size! May cause issues.")
except Exception as e:
    print(f"  ✓ Correctly rejected: {e}")

print("\n" + "-"*70)
print("\n[3] Live microphone test with synthetic comparison")
print("-"*70)

MIC_DEVICE = 17  # Elgato Wave:3
NATIVE_RATE = 48000
CHUNK_48K = CHUNK_SIZE * 3

mic_scores = []
synthetic_scores = []
chunk_count = 0
max_chunks = 30  # 30 chunks = ~2.4 seconds

def callback(indata, frames, time, status):
    global chunk_count
    if status:
        print(f"Stream status: {status}")
    
    if chunk_count >= max_chunks:
        raise sd.CallbackStop
    
    try:
        # Process real microphone audio
        audio_mono = indata[:, 0] if len(indata.shape) == 2 else indata
        audio_16k = signal.resample_poly(audio_mono, 1, 3)
        
        # Ensure exact size
        if len(audio_16k) != CHUNK_SIZE:
            if len(audio_16k) < CHUNK_SIZE:
                audio_16k = np.pad(audio_16k, (0, CHUNK_SIZE - len(audio_16k)))
            else:
                audio_16k = audio_16k[:CHUNK_SIZE]
        
        audio_16k = np.ascontiguousarray(audio_16k, dtype=np.float32)
        
        # Get score from real mic
        predictions = wake_model.predict(audio_16k)
        mic_score = predictions.get(WAKE_WORD, 0.0)
        mic_scores.append(mic_score)
        
        # Generate synthetic noise with same stats
        synth = np.random.randn(CHUNK_SIZE).astype(np.float32) * audio_16k.std()
        synth_predictions = wake_model.predict(synth)
        synth_score = synth_predictions.get(WAKE_WORD, 0.0)
        synthetic_scores.append(synth_score)
        
        # Compare
        indicator = "📢" if mic_score > 0.1 else "🔇"
        print(f"{indicator} Chunk {chunk_count+1}/30: Mic={mic_score:.4f} | Synth={synth_score:.4f} | "
              f"Range=[{audio_16k.min():.3f}, {audio_16k.max():.3f}]")
        
        chunk_count += 1
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

print("\n🎤 Recording from microphone for ~2.4 seconds...")
print("   (Stay quiet to establish noise floor)\n")

try:
    with sd.InputStream(
        samplerate=NATIVE_RATE,
        device=MIC_DEVICE,
        channels=1,
        callback=callback,
        blocksize=CHUNK_48K,
        dtype='float32'
    ):
        while chunk_count < max_chunks:
            sd.sleep(100)
except KeyboardInterrupt:
    print("\n\nStopped early")
except Exception as e:
    print(f"\nStream error: {e}")

print("\n" + "="*70)
print("ANALYSIS")
print("="*70)

if mic_scores:
    mic_avg = np.mean(mic_scores)
    mic_max = np.max(mic_scores)
    synth_avg = np.mean(synthetic_scores)
    
    print(f"\nMicrophone audio:")
    print(f"  Average score: {mic_avg:.6f}")
    print(f"  Max score: {mic_max:.6f}")
    print(f"  Detections (>0.1): {sum(1 for s in mic_scores if s > 0.1)}")
    
    print(f"\nSynthetic noise:")
    print(f"  Average score: {synth_avg:.6f}")
    
    print(f"\n🔍 Diagnosis:")
    
    if mic_avg == 0.0 and mic_max == 0.0:
        print("  ❌ CRITICAL: All microphone scores are exactly 0.0")
        print("     → Data type mismatch or invalid audio format")
        print("     → Check ANALYSIS.md for fixes")
    elif mic_avg < 0.001:
        print("  ⚠ Scores extremely low but not zero")
        print("     → Audio is being processed, but:")
        print("       - Check microphone volume/gain")
        print("       - Verify correct device selected")
        print("       - May need to speak louder")
    elif mic_avg > 0.01 and mic_avg < 0.1:
        print("  ✓ Normal noise floor detected")
        print("     → System is working correctly")
        print("     → Speak the wake word to test detection")
    elif mic_avg > 0.1:
        print("  ⚠ Suspiciously high scores on silence/noise")
        print("     → May indicate false positive issues")
        print("     → Consider raising WAKE_THRESHOLD")
    
    # Compare with synthetic
    if abs(mic_avg - synth_avg) < 0.001:
        print("\n  ℹ Mic and synthetic have similar scores")
        print("     → Hardware is working, audio reaching model")
    elif mic_avg < synth_avg / 10:
        print("\n  ⚠ Mic scores much lower than synthetic")
        print("     → Possible amplitude/normalization issue")
else:
    print("\n❌ No data collected - check device configuration")

print("\n✓ Test complete")
print("\nNext steps:")
print("  1. If all scores are 0.0 → Run ANALYSIS.md fixes")
print("  2. If scores are 0.001-0.01 → Run diagnostic_listener.py and speak")
print("  3. If scores look good → Run fixed_listener.py for production use")
