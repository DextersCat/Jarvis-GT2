"""
Quick test for Elgato Wave:3 microphone
"""
import sounddevice as sd
import numpy as np

DEVICE = 17  # Elgato Wave:3

print("Testing Elgato Wave:3 (device 17)")
print("="*60)

# Check device info
try:
    info = sd.query_devices(DEVICE)
    print(f"\nDevice: {info['name']}")
    print(f"Max input channels: {info['max_input_channels']}")
    print(f"Default sample rate: {info['default_samplerate']}")
except Exception as e:
    print(f"ERROR: Cannot access device 17: {e}")
    print("\nTrying to find Elgato automatically...")
    devices = sd.query_devices()
    for i, dev in enumerate(devices):
        if 'elgato' in dev['name'].lower() or 'wave' in dev['name'].lower():
            print(f"  Found: Device {i}: {dev['name']} ({dev['max_input_channels']} inputs)")
    exit(1)

# Test recording
print("\n" + "="*60)
print("Recording 2 seconds - SPEAK NOW!")
print("="*60)

try:
    recording = sd.rec(
        int(2 * 48000),
        samplerate=48000,
        device=DEVICE,
        channels=1,
        dtype='float32'
    )
    sd.wait()
    
    print(f"\n✓ Recording complete!")
    print(f"  Shape: {recording.shape}")
    print(f"  Range: [{recording.min():.6f}, {recording.max():.6f}]")
    print(f"  Mean: {recording.mean():.6f}")
    print(f"  Std: {recording.std():.6f}")
    print(f"  Non-zero samples: {np.count_nonzero(recording):,}/{len(recording):,}")
    
    # Check if audio was captured
    if recording.max() == 0 and recording.min() == 0:
        print("\n❌ PROBLEM: All zeros - microphone not capturing!")
        print("   → Check Windows microphone permissions")
        print("   → Check if Elgato Wave:3 is selected as input device")
    elif abs(recording.max()) < 0.001:
        print("\n⚠ WARNING: Very low volume")
        print("   → Check microphone gain/volume")
    else:
        print("\n✓ Microphone is working!")
        
        # Show volume histogram
        print("\n  Volume distribution:")
        abs_vals = np.abs(recording)
        bins = [0.001, 0.01, 0.1, 0.5, 1.0]
        for i in range(len(bins)):
            if i == 0:
                count = np.sum(abs_vals < bins[i])
                print(f"    < {bins[i]}: {count:,} samples")
            else:
                count = np.sum((abs_vals >= bins[i-1]) & (abs_vals < bins[i]))
                print(f"    {bins[i-1]}-{bins[i]}: {count:,} samples")
        
except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
