"""
Test to verify yes.wav generation and playback
"""
import os
import subprocess

print("="*60)
print("  YES.WAV AUDIO ASSET TEST")
print("="*60)

print("\n[1/4] Checking for Piper installation...")
try:
    result = subprocess.run(
        ["piper", "--version"],
        capture_output=True,
        timeout=3
    )
    print(f"  ✓ Piper installed: {result.stdout.decode().strip()}")
    piper_available = True
except FileNotFoundError:
    print("  ✗ Piper not found in PATH")
    print("  Install: https://github.com/rhasspy/piper")
    piper_available = False
except Exception as e:
    print(f"  ✗ Error checking Piper: {e}")
    piper_available = False

print("\n[2/4] Checking for yes.wav file...")
if os.path.exists("yes.wav"):
    size = os.path.getsize("yes.wav")
    print(f"  ✓ yes.wav exists ({size} bytes)")
else:
    print("  ✗ yes.wav not found")
    if piper_available:
        print("  Attempting to generate...")
        try:
            result = subprocess.run(
                ["piper", "--model", "en_US-lessac-medium", "--output_file", "yes.wav"],
                input="Yes?".encode(),
                capture_output=True,
                timeout=10
            )
            if result.returncode == 0:
                print("  ✓ yes.wav generated successfully!")
            else:
                print(f"  ✗ Generation failed: {result.stderr.decode()}")
        except Exception as e:
            print(f"  ✗ Error generating: {e}")

print("\n[3/4] Testing audio playback...")
if os.path.exists("yes.wav"):
    try:
        abs_path = os.path.abspath("yes.wav")
        print(f"  Playing: {abs_path}")
        result = subprocess.run(
            ["powershell", "-c", f"(New-Object Media.SoundPlayer '{abs_path}').PlaySync();"],
            capture_output=True,
            timeout=5
        )
        if result.returncode == 0:
            print("  ✓ Audio played successfully!")
        else:
            print(f"  ✗ Playback failed: {result.stderr.decode()}")
    except Exception as e:
        print(f"  ✗ Error playing audio: {e}")
else:
    print("  ⊘ Skipped - no audio file")

print("\n[4/4] Checking jarvisgt2.py integration...")
with open('jarvisgt2.py', 'r', encoding='utf-8') as f:
    code = f.read()

checks = {
    'generate_yes_audio method': 'def generate_yes_audio(self):' in code,
    'play_yes_audio method': 'def play_yes_audio(self):' in code,
    'yes.wav generation call': 'self.generate_yes_audio()' in code,
    'play on wake word': 'self.play_yes_audio()' in code
}

for check, result in checks.items():
    status = "✓" if result else "✗"
    print(f"  {status} {check}")

print("\n" + "="*60)
print("  SUMMARY")
print("="*60)

if not piper_available:
    print("\n  ⚠️  PIPER NOT INSTALLED")
    print("  Download Piper TTS to enable audio acknowledgment")
    print("  https://github.com/rhasspy/piper/releases")
elif not os.path.exists("yes.wav"):
    print("\n  ⚠️  yes.wav NOT GENERATED")
    print("  Run jarvisgt2.py once to auto-generate the file")
else:
    print("\n  ✓ YES.WAV READY")
    print("  Wake word acknowledgment will work correctly")

print("="*60 + "\n")
