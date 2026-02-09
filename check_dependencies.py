"""
Comprehensive Jarvis GT2 Dependency Check
"""
import subprocess
import sys

def check_command(cmd, name):
    """Check if a command is available"""
    try:
        result = subprocess.run(cmd, capture_output=True, timeout=3)
        return True, result.stdout.decode().strip() if result.stdout else "OK"
    except FileNotFoundError:
        return False, "Not found"
    except Exception as e:
        return False, str(e)

def check_import(module_name, display_name=None):
    """Check if a Python module can be imported"""
    if display_name is None:
        display_name = module_name
    try:
        __import__(module_name)
        return True, "OK"
    except ImportError as e:
        return False, str(e)
    except Exception as e:
        return False, str(e)

print("="*70)
print("  JARVIS GT2 DEPENDENCY CHECK")
print("="*70)

print("\n🐍 PYTHON PACKAGES")
print("-"*70)

packages = [
    ("customtkinter", "CustomTkinter (GUI)"),
    ("pvporcupine", "Porcupine (Wake word)"),
    ("pvrecorder", "PvRecorder (Audio)"),
    ("whisper", "Whisper (STT)"),
    ("numpy", "NumPy"),
    ("numba", "Numba (Whisper dependency)"),
    ("requests", "Requests (API calls)"),
    ("googleapiclient", "Google API Client"),
    ("google.auth", "Google Auth"),
]

all_python_ok = True
for module, name in packages:
    ok, msg = check_import(module, name)
    status = "✓" if ok else "✗"
    print(f"  {status} {name:30} {msg if not ok else ''}")
    if not ok:
        all_python_ok = False

print("\n🔧 EXTERNAL TOOLS")
print("-"*70)

tools = [
    (["piper", "--version"], "Piper TTS (Voice synthesis)", False),  # Optional
]

piper_ok = True
for cmd, name, required in tools:
    ok, msg = check_command(cmd, name)
    status = "✓" if ok else ("⚠" if not required else "✗")
    req_text = "" if required else " (Optional)"
    print(f"  {status} {name:30} {msg[:40] if ok else 'Not installed'}{req_text}")
    if not ok and name.startswith("Piper"):
        piper_ok = False

print("\n📋 SUMMARY")
print("-"*70)

if all_python_ok:
    print("  ✅ All Python dependencies installed")
else:
    print("  ❌ Some Python packages missing - run:")
    print("     pip install -r requirements.txt")

if not piper_ok:
    print("  ⚠️  Piper TTS not installed (optional)")
    print("     • Will use beep fallback for wake word acknowledgment")
    print("     • Install guide: python PIPER_SETUP.py")
else:
    print("  ✅ Piper TTS installed - voice acknowledgment available")

print("\n🚀 SYSTEM STATUS")
print("-"*70)

if all_python_ok:
    print("  ✓ Wake word detection: Ready")
    print("  ✓ Speech-to-text (Whisper): Ready")
    print("  ✓ LLM integration: Ready")
    print("  ✓ Google API: Ready")
    if piper_ok:
        print("  ✓ Voice synthesis: Ready")
    else:
        print("  ⚠ Voice synthesis: Beep fallback only")
    
    print("\n  🎉 JARVIS GT2 IS READY TO RUN!")
    print("     Command: python jarvisgt2.py")
else:
    print("  ❌ Cannot start - missing required dependencies")
    
print("="*70)
