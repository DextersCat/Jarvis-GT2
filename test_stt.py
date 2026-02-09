"""
Test Speech-To-Text to verify microphone audio quality
"""
import sounddevice as sd
import numpy as np
import whisper
import tempfile
from scipy.io.wavfile import write

DEVICE = 17  # Elgato Wave:3
SAMPLE_RATE = 16000  # Whisper uses 16kHz
DURATION = 5  # Record for 5 seconds

print("="*70)
print("MICROPHONE → WHISPER STT TEST")
print("="*70)

print("\nLoading Whisper model (base)...")
stt_model = whisper.load_model("base")
print("✓ Whisper loaded")

print("\n" + "="*70)
print(f"Recording {DURATION} seconds from Elgato Wave:3")
print("Speak clearly - say anything you want!")
print("="*70 + "\n")

input("Press ENTER when ready to record...")

print(f"\n🎤 RECORDING FOR {DURATION} SECONDS - SPEAK NOW!")
print("-" * 70)

# Record at 16kHz directly (what Whisper expects)
try:
    audio = sd.rec(
        int(DURATION * SAMPLE_RATE),
        samplerate=SAMPLE_RATE,
        device=DEVICE,
        channels=1,
        dtype='float32'
    )
    sd.wait()
    print("✓ Recording complete")
except Exception as e:
    print(f"✗ Recording failed: {e}")
    print("\nTrying with 48kHz and resampling...")
    import scipy.signal as signal
    audio_48k = sd.rec(
        int(DURATION * 48000),
        samplerate=48000,
        device=DEVICE,
        channels=1,
        dtype='float32'
    )
    sd.wait()
    audio_mono = audio_48k.flatten()
    audio_16k = signal.resample_poly(audio_mono, 1, 3)
    audio = audio_16k.reshape(-1, 1)
    print("✓ Recording complete (resampled)")

# Check audio quality
audio_flat = audio.flatten()
print(f"\nAudio stats:")
print(f"  Duration: {len(audio_flat)/SAMPLE_RATE:.1f} seconds")
print(f"  Range: [{audio_flat.min():.3f}, {audio_flat.max():.3f}]")
print(f"  Mean: {audio_flat.mean():.6f}")
print(f"  RMS: {np.sqrt(np.mean(audio_flat**2)):.6f}")

if audio_flat.max() < 0.01:
    print("  ⚠ WARNING: Very quiet audio!")

# Save to temporary WAV file for Whisper
temp_wav = tempfile.mktemp(suffix='.wav')
try:
    # Whisper expects int16 PCM
    audio_int16 = (audio_flat * 32767).astype(np.int16)
    write(temp_wav, SAMPLE_RATE, audio_int16)
    
    print(f"\n🧠 Transcribing with Whisper...")
    print("-" * 70)
    
    result = stt_model.transcribe(temp_wav, fp16=False)
    
    print(f"\n{'='*70}")
    print("TRANSCRIPTION RESULTS")
    print("="*70)
    print(f"\nText: \"{result['text']}\"")
    print(f"\nLanguage: {result['language']}")
    
    if result['text'].strip():
        print("\n✓ SUCCESS! Microphone is working and capturing speech!")
        print("\nSegments:")
        for i, segment in enumerate(result['segments']):
            start = segment['start']
            end = segment['end']
            text = segment['text']
            print(f"  [{start:5.1f}s - {end:5.1f}s]: {text}")
    else:
        print("\n⚠ No speech detected")
        print("  → Check if you spoke during recording")
        print("  → Check microphone volume/gain")
    
finally:
    import os
    if os.path.exists(temp_wav):
        os.remove(temp_wav)

print("\n" + "="*70)
print("TEST COMPLETE")
print("="*70)
print("\nIf transcription worked, your microphone and audio pipeline are fine.")
print("The wake word issue is specific to openWakeWord, not your hardware.")
