"""
Quick diagnostic test for Porcupine wake word detection
Tests if "Jarvis" wake word can be detected
"""
import pvporcupine
from pvrecorder import PvRecorder
import time

PICOVOICE_KEY = "VUq4dvkzHgfslR1FiHg6Oxt6ab0kYnjABDoO5V1Pu14PJRm6EI34IQ=="

def test_wake_word():
    print("="*60)
    print("  WAKE WORD DETECTION TEST")
    print("="*60)
    
    # Test 1: Check available devices
    print("\n[1/4] Checking available audio devices...")
    try:
        devices = PvRecorder.get_available_devices()
        print(f"  ✓ Found {len(devices)} device(s):")
        for i, device in enumerate(devices):
            print(f"    {i}: {device}")
    except Exception as e:
        print(f"  ✗ Error getting devices: {e}")
        return
    
    # Test 2: Create Porcupine instance
    print("\n[2/4] Creating Porcupine wake word engine...")
    try:
        porcupine = pvporcupine.create(
            access_key=PICOVOICE_KEY,
            keywords=['jarvis']
        )
        print(f"  ✓ Porcupine created successfully")
        print(f"  Frame length: {porcupine.frame_length}")
        print(f"  Sample rate: {porcupine.sample_rate}")
        print(f"  Version: {porcupine.version}")
    except Exception as e:
        print(f"  ✗ Error creating Porcupine: {e}")
        return
    
    # Test 3: Create recorder
    print("\n[3/4] Creating audio recorder...")
    try:
        recorder = PvRecorder(
            device_index=-1,  # default device
            frame_length=porcupine.frame_length
        )
        print(f"  ✓ Recorder created successfully")
        print(f"  Using default device (index: -1)")
    except Exception as e:
        print(f"  ✗ Error creating recorder: {e}")
        porcupine.delete()
        return
    
    # Test 4: Listen for wake word
    print("\n[4/4] Starting wake word detection...")
    print("\n" + "="*60)
    print("  🎤 SAY 'JARVIS' NOW! (listening for 15 seconds)")
    print("="*60 + "\n")
    
    try:
        recorder.start()
        start_time = time.time()
        frame_count = 0
        detected = False
        
        while time.time() - start_time < 15:  # Listen for 15 seconds
            pcm = recorder.read()
            frame_count += 1
            
            # Show progress every second
            if frame_count % 50 == 0:  # ~1 second at 50Hz
                elapsed = int(time.time() - start_time)
                remaining = 15 - elapsed
                print(f"  [{elapsed}s] Listening... {remaining}s remaining")
            
            keyword_index = porcupine.process(pcm)
            
            if keyword_index >= 0:
                print(f"\n  🎉 ✓ WAKE WORD DETECTED! (index: {keyword_index})")
                print(f"  Detected after {frame_count} frames (~{frame_count/50:.1f} seconds)")
                detected = True
                break
        
        recorder.stop()
        
        if not detected:
            print(f"\n  ⚠️  No wake word detected in 15 seconds")
            print(f"  Processed {frame_count} audio frames")
            print(f"\n  Troubleshooting:")
            print(f"    1. Check if your microphone is working")
            print(f"    2. Speak clearly and say 'JARVIS' at normal volume")
            print(f"    3. Check if another app is using the microphone")
            print(f"    4. Try moving closer to the microphone")
        
    except Exception as e:
        print(f"\n  ✗ Error during detection: {e}")
    finally:
        print("\n" + "="*60)
        print("  Cleaning up...")
        try:
            recorder.delete()
            porcupine.delete()
            print("  ✓ Cleanup complete")
        except Exception as e:
            print(f"  ⚠️  Cleanup error: {e}")
    
    print("="*60 + "\n")

if __name__ == "__main__":
    test_wake_word()
