"""
Test MULTIPLE models to find which ones actually work
"""
import numpy as np
import sounddevice as sd
import scipy.signal as signal
from openwakeword.model import Model

DEVICE = 17
TEST_MODELS = ["alexa", "hey_mycroft", "hey_rhasspy"]

print("="*70)
print("TESTING MULTIPLE WAKE WORD MODELS")
print("="*70)

print("\n📝 We'll test these models:")
for model in TEST_MODELS:
    print(f"  • {model}")

print("\n" + "="*70)
print("Recording 5 seconds - Say MULTIPLE wake words:")
print("  'ALEXA' ... 'HEY MYCROFT' ... 'HEY RHASSPY'")
print("="*70 + "\n")

input("Press ENTER when ready...")

audio_48k = sd.rec(int(5 * 48000), samplerate=48000, device=DEVICE, channels=1, dtype='float32')
print("🎤 RECORDING NOW - Say: ALEXA ... HEY MYCROFT ... HEY RHASSPY")
sd.wait()
print("✓ Recording complete\n")

# Process audio
audio_mono = audio_48k.flatten()
audio_16k = signal.resample_poly(audio_mono, 1, 3)

print(f"Audio captured - Range: [{audio_mono.min():.3f}, {audio_mono.max():.3f}]")

# Test each model
results = {}

for model_name in TEST_MODELS:
    print(f"\n{'='*70}")
    print(f"Testing: {model_name}")
    print("="*70)
    
    try:
        # Load model (try ONNX first, fallback to TFLite)
        wake_model = Model(wakeword_models=[model_name], inference_framework="onnx")
        print(f"✓ Loaded {model_name}")
        
        max_score = 0
        detections = []
        num_chunks = len(audio_16k) // 1280
        
        for i in range(num_chunks):
            chunk = audio_16k[i*1280:(i+1)*1280]
            chunk = np.ascontiguousarray(chunk, dtype=np.float32)
            
            predictions = wake_model.predict(chunk)
            score = predictions.get(model_name, 0.0)
            
            if score > max_score:
                max_score = score
            
            if score > 0.05:  # Lower threshold to catch weak detections
                time_sec = i * 1280 / 16000
                bar = "█" * int(score * 40)
                print(f"  @ {time_sec:4.1f}s: {score:.4f} [{bar}]")
                detections.append((time_sec, score))
        
        results[model_name] = {
            'max': max_score,
            'count': len(detections)
        }
        
        if max_score > 0.3:
            print(f"  ✓ STRONG DETECTION: {max_score:.4f}")
        elif max_score > 0.1:
            print(f"  ⚠ Weak detection: {max_score:.4f}")
        elif max_score > 0.01:
            print(f"  ⚠ Very weak: {max_score:.4f}")
        else:
            print(f"  ❌ No detection: {max_score:.4f}")
            
    except Exception as e:
        print(f"  ✗ Error: {e}")
        results[model_name] = {'max': 0, 'count': 0, 'error': str(e)}

# Summary
print("\n" + "="*70)
print("SUMMARY")
print("="*70)

for model_name, result in results.items():
    if 'error' in result:
        print(f"{model_name:20s}: ERROR - {result['error']}")
    else:
        max_score = result['max']
        count = result['count']
        if max_score > 0.3:
            status = "✓ WORKS"
        elif max_score > 0.1:
            status = "⚠ WEAK"
        else:
            status = "❌ BROKEN"
        print(f"{model_name:20s}: {status} | Max: {max_score:.4f} | Detections: {count}")

print("\n💡 Recommendation:")
best_model = max(results.keys(), key=lambda k: results[k]['max'])
best_score = results[best_model]['max']

if best_score > 0.3:
    print(f"   Use '{best_model}' - it works with score {best_score:.4f}")
    print(f"   Change your code to use this wake word instead of 'hey_jarvis'")
elif best_score > 0.01:
    print(f"   '{best_model}' has weak detection ({best_score:.4f})")
    print("   Try speaking louder or adjusting microphone gain")
else:
    print("   ❌ NONE of the models worked!")
    print("   This suggests a fundamental issue with openWakeWord setup")
    print("   or the audio processing pipeline")
