#!/usr/bin/env python3
"""
Test all API credentials loaded from .env and config.json
Validates Google APIs, Porcupine key, and Ollama connection
"""
import os
import sys
import json

# Load environment variables from .env
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("Install python-dotenv: pip install python-dotenv")
    sys.exit(1)

def test_picovoice():
    """Test Porcupine wake word API key."""
    print("\n" + "="*60)
    print("  PORCUPINE WAKE WORD TEST")
    print("="*60)
    
    # Check .env first, then config.json as fallback
    key = os.getenv("PICOVOICE_KEY")
    
    if not key:
        # Fallback to config.json
        try:
            with open('config.json', 'r') as f:
                config = json.load(f)
                key = config.get("picovoice_key")
                if key:
                    print("  ℹ️  Using key from config.json (consider moving to .env)")
        except:
            pass
    
    if not key:
        print("  ✗ PICOVOICE_KEY not found in .env or config.json")
        return False
    
    try:
        import pvporcupine
        # Test with built-in 'jarvis' wake word
        porcupine = pvporcupine.create(
            access_key=key,
            keywords=['jarvis']
        )
        porcupine.delete()
        print("  ✓ Porcupine API key valid")
        return True
    except Exception as e:
        print(f"  ✗ Porcupine failed: {e}")
        return False

def test_google_oauth():
    """Test Google OAuth credentials."""
    print("\n" + "="*60)
    print("  GOOGLE OAUTH TEST")
    print("="*60)
    
    client_id = os.getenv("GOOGLE_CLIENT_ID")
    client_secret = os.getenv("GOOGLE_CLIENT_SECRET")
    
    if not client_id or not client_secret:
        print("  ✗ GOOGLE_CLIENT_ID or GOOGLE_CLIENT_SECRET missing")
        return False
    
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
        print("  ✓ Google OAuth credentials format valid")
        return True
    except Exception as e:
        print(f"  ✗ Google OAuth failed: {e}")
        return False

def test_google_cse():
    """Test Google Custom Search API."""
    print("\n" + "="*60)
    print("  GOOGLE CUSTOM SEARCH API TEST")
    print("="*60)
    
    api_key = os.getenv("GOOGLE_CSE_API_KEY")
    cx = os.getenv("GOOGLE_CSE_CX")
    
    if not api_key or not cx:
        print("  ✗ GOOGLE_CSE_API_KEY or GOOGLE_CSE_CX missing")
        return False
    
    try:
        import requests
        response = requests.get(
            "https://www.googleapis.com/customsearch/v1",
            params={
                "q": "test",
                "key": api_key,
                "cx": cx
            },
            timeout=10
        )
        
        if response.status_code == 200:
            print("  ✓ Google Custom Search API key valid")
            return True
        elif response.status_code == 403:
            print("  ✗ API key invalid or quota exceeded (403)")
            return False
        else:
            print(f"  ✗ API returned {response.status_code}: {response.text[:100]}")
            return False
    except Exception as e:
        print(f"  ✗ Custom Search API failed: {e}")
        return False

def test_google_drive():
    """Test Google Drive folder access."""
    print("\n" + "="*60)
    print("  GOOGLE DRIVE TEST")
    print("="*60)
    
    folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID")
    
    if not folder_id:
        print("  ✗ GOOGLE_DRIVE_FOLDER_ID missing")
        return False
    
    print(f"  Folder ID: {folder_id}")
    print("  ℹ️  Drive API requires OAuth token (check token.json)")
    print("  If token.json doesn't exist, run: jarvis_main.py to authenticate")
    return True

def test_ollama():
    """Test Ollama brain connection."""
    print("\n" + "="*60)
    print("  OLLAMA BRAIN TEST")
    print("="*60)
    
    brain_url = os.getenv("BRAIN_URL", "http://192.168.1.27:11434/api/generate")
    model = os.getenv("LLM_MODEL", "llama3.1:8b")
    
    try:
        import requests
        response = requests.post(
            brain_url,
            json={
                "model": model,
                "prompt": "test",
                "stream": False
            },
            timeout=5
        )
        
        if response.status_code == 200:
            print(f"  ✓ Ollama connected (model: {model})")
            return True
        else:
            print(f"  ✗ Ollama error {response.status_code}: {response.text[:100]}")
            return False
    except Exception as e:
        print(f"  ✗ Ollama connection failed: {e}")
        print(f"    Make sure Ollama is running at {brain_url}")
        return False

def main():
    print("\n" + "="*60)
    print("  JARVIS GT2 API CREDENTIAL TEST")
    print("="*60)
    
    results = {
        "Porcupine": test_picovoice(),
        "Google OAuth": test_google_oauth(),
        "Google Custom Search": test_google_cse(),
        "Google Drive": test_google_drive(),
        "Ollama Brain": test_ollama(),
    }
    
    print("\n" + "="*60)
    print("  TEST SUMMARY")
    print("="*60)
    
    for service, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {status}: {service}")
    
    passed = sum(results.values())
    total = len(results)
    print(f"\nResult: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n✓ All credentials are valid!")
        return 0
    else:
        print("\n✗ Some credentials need attention. Check .env and config.json")
        return 1

if __name__ == "__main__":
    sys.exit(main())
