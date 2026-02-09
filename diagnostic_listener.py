"""
MINIMAL VIABLE LISTENER - OpenWakeWord Diagnostic Tool
Displays raw probability arrays and audio characteristics
"""
import numpy as np
import sounddevice as sd
import scipy.signal as signal
from openwakeword.model import Model
import sys

# --- CONFIGURATION ---
WAKE_WORD = "hey_jarvis"
MIC_DEVICE_INDEX = 17  # Elgato Wave:3
NATIVE_RATE = 48000  # Your mic's native rate
TARGET_RATE = 16000  # OpenWakeWord requirement
CHUNK_SIZE_16K = 1280  # Required frame size at 16kHz
CHUNK_SIZE_48K = CHUNK_SIZE_16K * 3  # 3840 samples at 48kHz

print("=" * 70)
print("DIAGNOSTIC LISTENER - OpenWakeWord Analysis")
print("=" * 70)

# Initialize model
print(f"\n[1/4] Loading model for '{WAKE_WORD}'...")
try:
    wake_model = Model(wakeword_models=[WAKE_WORD], inference_framework="onnx")
    print("✓ Model loaded successfully")
except Exception as e:
    print(f"✗ Model loading failed: {e}")
    sys.exit(1)

# Audio statistics tracker
audio_stats = {
    'min': 0, 'max': 0, 'mean': 0, 'std': 0,
    'zero_count': 0, 'total_chunks': 0
}

def analyze_audio_chunk(audio_data):
    """Analyze audio characteristics"""
    audio_stats['min'] = min(audio_stats['min'], audio_data.min())
    audio_stats['max'] = max(audio_stats['max'], audio_data.max())
    audio_stats['mean'] = audio_data.mean()
    audio_stats['std'] = audio_data.std()
    audio_stats['zero_count'] += np.sum(audio_data == 0)
    audio_stats['total_chunks'] += 1

def callback(indata, frames, time, status):
    """Process audio stream"""
    if status:
        print(f"\n⚠ Stream status: {status}")
    
    try:
        # --- DIAGNOSTIC STEP 1: Check input shape and type ---
        print(f"\n[INPUT RAW]")
        print(f"  Shape: {indata.shape} | dtype: {indata.dtype}")
        print(f"  Range: [{indata.min():.6f}, {indata.max():.6f}]")
        
        # --- DIAGNOSTIC STEP 2: Extract mono channel correctly ---
        if len(indata.shape) == 2:
            audio_mono = indata[:, 0]
        else:
            audio_mono = indata
        
        print(f"  After mono: shape={audio_mono.shape}")
        
        # --- DIAGNOSTIC STEP 3: Resample to 16kHz ---
        # Using scipy's resample_poly (high quality)
        audio_16k = signal.resample_poly(audio_mono, 1, 3)
        
        print(f"\n[RESAMPLED]")
        print(f"  Shape: {audio_16k.shape} | Expected: {CHUNK_SIZE_16K}")
        print(f"  Range: [{audio_16k.min():.6f}, {audio_16k.max():.6f}]")
        
        # Check if resampled size matches expected
        if audio_16k.shape[0] != CHUNK_SIZE_16K:
            print(f"  ⚠ SIZE MISMATCH! Got {audio_16k.shape[0]}, need {CHUNK_SIZE_16K}")
        
        # --- DIAGNOSTIC STEP 4: Ensure correct data type ---
        # OpenWakeWord expects float32
        audio_float32 = audio_16k.astype(np.float32)
        
        # Analyze audio characteristics
        analyze_audio_chunk(audio_float32)
        
        # --- DIAGNOSTIC STEP 5: Feed to model and get RAW predictions ---
        predictions = wake_model.predict(audio_float32)
        
        print(f"\n[MODEL OUTPUT]")
        print(f"  Raw predictions dict: {predictions}")
        
        # Extract confidence score
        score = predictions.get(WAKE_WORD, 0.0)
        
        # --- DIAGNOSTIC STEP 6: Show probability breakdown ---
        print(f"\n[CONFIDENCE ANALYSIS]")
        print(f"  Wake word: {WAKE_WORD}")
        print(f"  Score: {score:.6f}")
        print(f"  Percentage: {score * 100:.2f}%")
        
        # Visual bar for confidence (0-100%)
        bar_length = int(score * 50)
        bar = "█" * bar_length + "░" * (50 - bar_length)
        print(f"  [{bar}]")
        
        # Check for issues
        if score == 0.0:
            print("\n⚠ ZERO CONFIDENCE - Possible issues:")
            print("  • Audio might be all zeros (mic not working)")
            print("  • Data type mismatch")
            print("  • Audio not normalized correctly")
            print("  • Wrong channel selected")
        elif score < 0.01:
            print("\n⚠ Very low confidence (<1%) - Check:")
            print("  • Audio quality/volume")
            print("  • Background noise")
            print("  • Resampling artifacts")
        
        print("\n" + "─" * 70)
        
        # Show cumulative stats every 10 chunks
        if audio_stats['total_chunks'] % 10 == 0:
            print(f"\n[CUMULATIVE STATS after {audio_stats['total_chunks']} chunks]")
            print(f"  Audio range: [{audio_stats['min']:.6f}, {audio_stats['max']:.6f}]")
            print(f"  Mean: {audio_stats['mean']:.6f} | Std: {audio_stats['std']:.6f}")
            if audio_stats['zero_count'] > 0:
                print(f"  ⚠ Zero samples detected: {audio_stats['zero_count']}")
        
    except Exception as e:
        print(f"\n✗ ERROR in callback: {e}")
        import traceback
        traceback.print_exc()

print(f"\n[2/4] Checking microphone...")
print(f"  Device index: {MIC_DEVICE_INDEX}")
try:
    device_info = sd.query_devices(MIC_DEVICE_INDEX)
    print(f"  Name: {device_info['name']}")
    print(f"  Max input channels: {device_info['max_input_channels']}")
    print(f"  Default sample rate: {device_info['default_samplerate']}")
except Exception as e:
    print(f"✗ Could not query device: {e}")
    sys.exit(1)

print(f"\n[3/4] Stream configuration:")
print(f"  Native rate: {NATIVE_RATE} Hz")
print(f"  Target rate: {TARGET_RATE} Hz")
print(f"  Blocksize: {CHUNK_SIZE_48K} samples @ 48kHz")
print(f"  After resample: {CHUNK_SIZE_16K} samples @ 16kHz")
print(f"  Duration per chunk: {CHUNK_SIZE_16K / TARGET_RATE * 1000:.1f} ms")

print(f"\n[4/4] Starting audio stream...")
print("=" * 70)
print("\n👂 LISTENING - Speak the wake word to test detection")
print("   Press Ctrl+C to stop\n")

try:
    with sd.InputStream(
        samplerate=NATIVE_RATE,
        device=MIC_DEVICE_INDEX,
        channels=1,  # Request mono explicitly
        callback=callback,
        blocksize=CHUNK_SIZE_48K,
        dtype='float32'  # Ensure float32 input
    ):
        while True:
            sd.sleep(1000)
            
except KeyboardInterrupt:
    print("\n\n" + "=" * 70)
    print("DIAGNOSTIC SESSION COMPLETE")
    print("=" * 70)
    print(f"\nTotal chunks processed: {audio_stats['total_chunks']}")
    print(f"Audio range observed: [{audio_stats['min']:.6f}, {audio_stats['max']:.6f}]")
    
    if audio_stats['max'] == 0 and audio_stats['min'] == 0:
        print("\n⚠ WARNING: All audio was zeros!")
        print("  → Microphone is not providing data")
        print("  → Check device permissions and selection")
    elif abs(audio_stats['max']) < 0.001:
        print("\n⚠ WARNING: Audio levels extremely low!")
        print("  → Check microphone volume/gain")
        print("  → Ensure correct input device selected")
    
    print("\n✓ Diagnostic complete")
