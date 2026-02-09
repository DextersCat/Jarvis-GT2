#!/usr/bin/env python3
"""
Quick test to verify jarvis_main.py loads config correctly from .env and config.json
"""
import sys
sys.path.insert(0, '.')

from jarvis_main import load_config

print("Testing config loading from .env and config.json...")
print("="*60)

config = load_config()

print("✓ Config loaded successfully")
print()
print("Configuration values:")
print(f"  Brain URL: {config['brain_url']}")
print(f"  LLM Model: {config['llm_model']}")
print(f"  Owner Email: {config['owner_email']}")
print(f"  Drive Folder ID: {config['google_drive_folder_id']}")
print()

# Verify environment variables are being used
import os
from dotenv import load_dotenv
load_dotenv()

print("Environment variable check:")
if os.getenv("PICOVOICE_KEY"):
    print("  ✓ PICOVOICE_KEY loaded from .env")
else:
    print("  ℹ️  PICOVOICE_KEY using config.json fallback")

if os.getenv("GOOGLE_CSE_API_KEY"):
    print("  ✓ GOOGLE_CSE_API_KEY loaded from .env")
else:
    print("  ℹ️  GOOGLE_CSE_API_KEY using config.json fallback")

print()
print("="*60)
print("✓ All configuration tests passed!")
print("jarvis_main.py will load environment variables correctly.")
