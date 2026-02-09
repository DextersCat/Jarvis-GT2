"""
Quick setup guide for Piper TTS
"""

print("="*70)
print("  PIPER TTS SETUP GUIDE FOR JARVIS GT2")
print("="*70)

print("""
Piper is a fast, local text-to-speech system that gives Jarvis a voice.

OPTION 1: Quick Install (Recommended)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Download Piper for Windows:
   https://github.com/rhasspy/piper/releases/latest
   
   Look for: piper_windows_amd64.zip (or arm64 if ARM)

2. Extract the ZIP file to a folder like:
   C:\\Tools\\piper\\

3. Add Piper to your PATH:
   - Press Win + X → System → Advanced system settings
   - Click "Environment Variables"
   - Under "User variables", select "Path" → Edit
   - Click "New" and add: C:\\Tools\\piper
   - Click OK on all windows

4. Download the voice model:
   https://github.com/rhasspy/piper/releases/download/2023.11.14-2/voice-en-us-lessac-medium.tar.gz
   
   Extract to: C:\\Tools\\piper\\

5. Restart PowerShell and test:
   piper --version

OPTION 2: Manual Setup
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
If you prefer not to add Piper to PATH, you can:
- Place piper.exe in your Jarvis folder
- Jarvis will use system beeps as fallback (already working)

CURRENT STATUS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✓ Wake word detection: Working
✓ Beep acknowledgment: Working (current fallback)
⚠ Voice acknowledgment: Requires Piper installation

WHAT HAPPENS NOW
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
- Without Piper: Double beep when you say "Jarvis" (working now)
- With Piper: Jarvis says "Yes?" in a natural voice (better UX)

Both work! The beep is fine if you don't want to install Piper.
""")

print("="*70)

# Check if Piper is installed
import subprocess
try:
    result = subprocess.run(["piper", "--version"], capture_output=True, timeout=2)
    print("\n✓ PIPER IS ALREADY INSTALLED!")
    print(f"  Version: {result.stdout.decode().strip()}")
except FileNotFoundError:
    print("\n⚠  Piper not detected in PATH")
    print("  Follow Option 1 above to install")
except Exception as e:
    print(f"\n⚠  Could not check Piper: {e}")

print("\n" + "="*70)
