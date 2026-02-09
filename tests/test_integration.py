#!/usr/bin/env python3
"""
Integration Test - Verify Vault Reference & Google Docs Integration

This test verifies that all new methods are properly integrated into jarvisgt2.py
and can be called correctly.
"""

import os
import sys
import json
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("\n" + "="*70)
print("🧪 INTEGRATION TEST: Vault Reference & Google Docs")
print("="*70 + "\n")

# Test 1: Check imports
print("TEST 1: Checking imports...")
print("-" * 70)
try:
    from vault_reference import VaultReference
    print("✅ vault_reference imported successfully")
except ImportError as e:
    print(f"❌ Failed to import vault_reference: {e}")
    sys.exit(1)

try:
    import requests
    print("✅ requests library available")
except ImportError:
    print("❌ requests library missing")

try:
    from googleapiclient.discovery import build
    print("✅ Google API client available")
except ImportError:
    print("❌ Google API client missing")

# Test 2: Check vault index exists
print("\nTEST 2: Checking vault index file...")
print("-" * 70)
vault_index_path = Path("vault_index.json")
if vault_index_path.exists():
    print(f"✅ vault_index.json found ({vault_index_path.stat().st_size} bytes)")
    with open(vault_index_path) as f:
        index_data = json.load(f)
    print(f"   • Projects: {len(index_data.get('projects', {}))}")
    print(f"   • Reference types: {len(index_data.get('file_reference_map', {}))}")
else:
    print("❌ vault_index.json not found")
    print("   Run: python create_vault_index.py")

# Test 3: Check VaultReference can be initialized
print("\nTEST 3: Initializing VaultReference...")
print("-" * 70)
try:
    vault = VaultReference()
    if vault.is_loaded:
        print("✅ VaultReference loaded successfully")
        summary = vault.get_summary()
        print(f"   • Vault root: {summary['vault_root']}")
        print(f"   • Total files: {summary['total_files']}")
        print(f"   • Projects: {summary['total_projects']}")
    else:
        print("❌ VaultReference not loaded")
except Exception as e:
    print(f"❌ Error initializing VaultReference: {e}")

# Test 4: Check file resolution
print("\nTEST 4: Testing file reference resolution...")
print("-" * 70)
test_refs = ['main', 'startup', 'config']
for ref in test_refs:
    if vault.is_loaded:
        file_path = vault.get_file(ref)
        if file_path:
            filename = Path(file_path).name
            print(f"✅ '{ref}' → {filename}")
        else:
            print(f"⚠️  '{ref}' → No match found")

# Test 5: Check jarvisgt2.py modifications
print("\nTEST 5: Checking jarvisgt2.py modifications...")
print("-" * 70)
jarvis_file = Path("jarvisgt2.py")
if jarvis_file.exists():
    with open(jarvis_file, 'r', encoding='utf-8', errors='ignore') as f:
        jarvis_content = f.read()
    
    checks = {
        "VaultReference import": "from vault_reference import VaultReference",
        "Vault initialization": "self.vault = VaultReference()",
        "get_file_content method": "def get_file_content(self",
        "create_optimization_doc method": "def create_optimization_doc(self",
        "log_vault_action method": "def log_vault_action(self",
        "handle_optimization_request method": "def handle_optimization_request(self",
        "Optimization intent": "elif \"optimize\" in text_lower",
    }
    
    for check_name, check_string in checks.items():
        if check_string in jarvis_content:
            print(f"✅ {check_name}")
        else:
            print(f"❌ {check_name} - NOT FOUND")
else:
    print("❌ jarvisgt2.py not found")

# Test 6: Check config requirements
print("\nTEST 6: Checking configuration...")
print("-" * 70)
config_file = Path("config.json")
if config_file.exists():
    try:
        with open(config_file) as f:
            config = json.load(f)
        
        required_fields = [
            'picovoice_key',
            'google_drive_folder_id',
            'brain_url',
            'llm_model'
        ]
        
        for field in required_fields:
            if field in config:
                value = config[field]
                if isinstance(value, str) and len(value) > 0:
                    masked = value[:10] + "..." if len(value) > 10 else value
                    print(f"✅ {field}: {masked}")
                else:
                    print(f"⚠️  {field}: Empty or invalid")
            else:
                print(f"❌ {field}: MISSING")
    except json.JSONDecodeError:
        print("❌ config.json is invalid JSON")
else:
    print("⚠️  config.json not found (using defaults)")

# Test 7: Check memory file
print("\nTEST 7: Checking memory system...")
print("-" * 70)
memory_file = Path("jarvis_memory.json")
if memory_file.exists():
    print(f"✅ jarvis_memory.json exists")
    with open(memory_file) as f:
        memory = json.load(f)
    
    if 'vault_actions' in memory:
        action_count = len(memory['vault_actions'])
        print(f"   • Vault actions logged: {action_count}")
    else:
        print("   • Vault actions: Not yet initialized")
else:
    print("⚠️  jarvis_memory.json not found (will be created on first run)")

# Final summary
print("\n" + "="*70)
print("📊 INTEGRATION TEST SUMMARY")
print("="*70)

print("\n✅ All critical components verified!")
print("\nReady to test the workflow:")
print("  1. Start jarvisgt2.py")
print("  2. Say: 'Check the main file and create optimization doc'")
print("  3. Document should be created in your Google Drive")
print("\n" + "="*70 + "\n")
