#!/usr/bin/env python3
"""
Complete Jarvis Startup Verification Test
Tests: Credentials, Config, Tokens, Voice, Vault, Google APIs, Memory
"""
import json
import os
import sys
from pathlib import Path

def test_files_exist():
    """Test that all required JSON files exist."""
    print("\n[1] CHECKING REQUIRED FILES...")
    files = {
        "config.json": "Application config",
        "token.json": "Google auth token",
        "credentials.json": "Google OAuth credentials",
        "vault_index.json": "Vault file index",
        "jarvis_memory.json": "Persistent memory",
        "jarvis-high.onnx": "Piper TTS model",
        "jarvis-high.onnx.json": "Model metadata",
    }
    
    results = {}
    for fname, desc in files.items():
        exists = Path(fname).exists()
        status = "✅" if exists else "❌"
        size = f"({Path(fname).stat().st_size} bytes)" if exists else ""
        print(f"  {status} {fname:25} {desc:30} {size}")
        results[fname] = exists
    
    return all(results.values())

def test_json_validity():
    """Test that JSON files are valid."""
    print("\n[2] VALIDATING JSON FILES...")
    json_files = ["config.json", "token.json", "vault_index.json", "jarvis_memory.json"]
    
    results = {}
    for fname in json_files:
        if not Path(fname).exists():
            print(f"  ⚠️ {fname:25} (not found, skipping)")
            continue
        
        try:
            with open(fname, 'r') as f:
                json.load(f)
            print(f"  ✅ {fname:25} (valid JSON)")
            results[fname] = True
        except json.JSONDecodeError as e:
            print(f"  ❌ {fname:25} (invalid JSON: {e})")
            results[fname] = False
    
    return all(results.values())

def test_config_content():
    """Test that config.json has required keys."""
    print("\n[3] CHECKING CONFIG.JSON CONTENT...")
    if not Path("config.json").exists():
        print("  ❌ config.json not found")
        return False
    
    with open("config.json") as f:
        config = json.load(f)
    
    required_keys = [
        "picovoice_key",
        "brain_url",
        "llm_model",
        "google_drive_folder_id",
        "google_client_id",
        "google_client_secret",
    ]
    
    results = {}
    for key in required_keys:
        has_key = key in config
        has_value = bool(config.get(key))
        status = "✅" if (has_key and has_value) else "⚠️" if has_key else "❌"
        val_preview = str(config.get(key))[:40] + "..." if has_value else "(empty)"
        print(f"  {status} {key:30} {val_preview}")
        results[key] = has_key and has_value
    
    return all(results.values())

def test_google_auth():
    """Test Google authentication."""
    print("\n[4] CHECKING GOOGLE AUTH...")
    
    if not Path("token.json").exists():
        print("  ❌ token.json not found (Google auth not configured)")
        return False
    
    try:
        with open("token.json") as f:
            token = json.load(f)
        
        # Check for auth token structure
        has_token = "access_token" in token
        has_refresh = "refresh_token" in token
        has_expiry = "expiry" in token
        
        print(f"  {'✅' if has_token else '⚠️'} access_token present")
        print(f"  {'✅' if has_refresh else '❌'} refresh_token present")
        print(f"  {'✅' if has_expiry else '⚠️'} expiry timestamp present")
        
        # Access tokens are often omitted at rest and refreshed at runtime.
        return has_refresh
    except Exception as e:
        print(f"  ❌ Error reading token.json: {e}")
        return False

def test_vault():
    """Test Vault Index."""
    print("\n[5] CHECKING VAULT INDEX...")
    
    if not Path("vault_index.json").exists():
        print("  ❌ vault_index.json not found")
        return False
    
    with open("vault_index.json") as f:
        vault = json.load(f)
    
    # Check structure
    has_projects = "projects" in vault
    has_mappings = "file_reference_map" in vault
    
    print(f"  {'✅' if has_projects else '❌'} projects section")
    print(f"  {'✅' if has_mappings else '❌'} file_reference_map section")
    
    if has_projects:
        num_projects = len(vault["projects"])
        print(f"     Files indexed: {num_projects}")
    
    if has_mappings:
        num_refs = len(vault["file_reference_map"])
        print(f"     File references: {num_refs}")
        for ref, path in list(vault["file_reference_map"].items())[:5]:
            resolved_path = path
            if isinstance(path, list) and path:
                resolved_path = path[0]
            if isinstance(resolved_path, dict):
                resolved_path = resolved_path.get("path")
            resolved_name = Path(resolved_path).name if resolved_path else "(empty)"
            print(f"       • '{ref}' → {resolved_name}")
    
    return has_projects and has_mappings

def test_memory():
    """Test Jarvis Memory."""
    print("\n[6] CHECKING JARVIS MEMORY...")
    
    if not Path("jarvis_memory.json").exists():
        print("  ⚠️ jarvis_memory.json not found (will be created on first run)")
        return True
    
    with open("jarvis_memory.json") as f:
        memory = json.load(f)
    
    has_profile = "master_profile" in memory
    has_facts = "facts" in memory
    has_location = "master_location" in memory
    
    print(f"  {'✅' if has_profile else '❌'} master_profile")
    print(f"  {'✅' if has_facts else '❌'} facts database")
    print(f"  {'✅' if has_location else '❌'} location config")
    
    if has_profile:
        profile = memory["master_profile"]
        name = profile.get("name", "Unknown")
        method = profile.get("working_method", "Unknown")
        print(f"     Name: {name}")
        print(f"     Method: {method}")
    
    return has_profile and has_facts

def test_imports():
    """Test critical imports."""
    print("\n[7] TESTING PYTHON IMPORTS...")
    
    imports = [
        ("customtkinter", "GUI"),
        ("pvporcupine", "Wake word"),
        ("whisper", "STT"),
        ("requests", "HTTP"),
        ("googleapiclient.discovery", "Google Docs API"),
        ("google.oauth2.credentials", "Google OAuth"),
        ("flask", "Webhooks"),
        ("numpy", "Audio processing"),
    ]
    
    results = {}
    for module_name, desc in imports:
        try:
            __import__(module_name)
            print(f"  ✅ {module_name:30} ({desc})")
            results[module_name] = True
        except ImportError as e:
            print(f"  ❌ {module_name:30} ({e})")
            results[module_name] = False
    
    return all(results.values())

def main():
    """Run all tests."""
    print("=" * 70)
    print("JARVIS STARTUP VERIFICATION TEST SUITE")
    print("=" * 70)
    
    tests = [
        ("Files Exist", test_files_exist),
        ("JSON Validity", test_json_validity),
        ("Config Content", test_config_content),
        ("Google Auth", test_google_auth),
        ("Vault Index", test_vault),
        ("Memory System", test_memory),
        ("Python Imports", test_imports),
    ]
    
    results = {}
    for test_name, test_func in tests:
        try:
            result = test_func()
            results[test_name] = result
        except Exception as e:
            print(f"  ❌ Test error: {e}")
            results[test_name] = False
    
    # Summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status:10} {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🚀 ALL TESTS PASSED - JARVIS IS READY!")
        return 0
    else:
        print(f"\n⚠️  {total - passed} tests failed - check errors above")
        return 1

if __name__ == "__main__":
    sys.exit(main())
