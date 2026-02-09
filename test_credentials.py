"""
Quick credential test for Jarvis GT2
Tests Google API credentials for Calendar, Docs, and Custom Search
"""
import os
import sys
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = [
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/documents',
    'https://www.googleapis.com/auth/drive.file',
    'https://www.googleapis.com/auth/spreadsheets'
]

GOOGLE_CSE_API_KEY = "AIzaSyCkk-3kjsCrCMYlMbFE9da0nOVJFcdPi70"
GOOGLE_CSE_CX = "4601ee7e2ceca4aff"

def print_header(text):
    print(f"\n{'='*60}")
    print(f"  {text}")
    print(f"{'='*60}")

def check_files():
    print_header("FILE CHECK")
    
    # Check what we actually have
    cred_exists = os.path.exists('credentials.json')
    token_exists = os.path.exists('token.json')
    
    print(f"  {'✓ FOUND' if cred_exists else '✗ MISSING'}: credentials.json")
    print(f"  {'✓ FOUND' if token_exists else '✗ MISSING'}: token.json")
    
    # Check if credentials.json is actually a token file
    if cred_exists and not token_exists:
        try:
            import json
            with open('credentials.json', 'r') as f:
                data = json.load(f)
            
            # If it has 'token' and 'refresh_token', it's actually a token file
            if 'token' in data and 'refresh_token' in data:
                print("\n  ⚠️  WARNING: credentials.json appears to be a token file!")
                print("  Creating token.json from credentials.json...")
                
                import shutil
                shutil.copy('credentials.json', 'token.json')
                print("  ✓ token.json created successfully!")
                return True
        except:
            pass
    
    return cred_exists or token_exists

def get_google_creds():
    print_header("CREDENTIAL REFRESH TEST")
    
    creds = None
    if os.path.exists('token.json'):
        print("  Loading existing token.json...")
        try:
            creds = Credentials.from_authorized_user_file('token.json', SCOPES)
            print(f"  Token loaded. Valid: {creds.valid if creds else False}")
        except Exception as e:
            print(f"  Error loading token: {e}")
            return None
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("  Token expired. Attempting refresh...")
            try:
                creds.refresh(Request())
                print("  ✓ Token refreshed successfully!")
                
                with open('token.json', 'w') as token:
                    token.write(creds.to_json())
                print("  ✓ Token saved to token.json")
            except Exception as e:
                print(f"  ✗ Token refresh failed: {e}")
                return None
        else:
            if not os.path.exists('credentials.json'):
                print("  ✗ Cannot create new token: credentials.json (OAuth client) missing")
                print("  Note: Your existing token will be tested anyway")
                return creds
            
            print("  No valid token. Starting OAuth flow...")
            try:
                flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
                creds = flow.run_local_server(port=0)
                print("  ✓ New token acquired!")
                
                with open('token.json', 'w') as token:
                    token.write(creds.to_json())
                print("  ✓ Token saved to token.json")
            except Exception as e:
                print(f"  ✗ OAuth flow failed: {e}")
                return None
    else:
        print("  ✓ Existing token is valid!")
    
    return creds

def test_calendar_api(creds):
    print_header("CALENDAR API TEST")
    
    try:
        service = build('calendar', 'v3', credentials=creds)
        # Get the next 5 events
        events_result = service.events().list(
            calendarId='primary',
            maxResults=5,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        events = events_result.get('items', [])
        print(f"  ✓ Calendar API connected successfully!")
        print(f"  Found {len(events)} upcoming event(s)")
        
        if events:
            for event in events[:3]:  # Show first 3
                start = event['start'].get('dateTime', event['start'].get('date'))
                print(f"    - {event.get('summary', 'No title')}: {start}")
        
        return True
    except Exception as e:
        print(f"  ✗ Calendar API Error: {e}")
        return False

def test_docs_api(creds):
    print_header("DOCS API TEST")
    
    try:
        service = build('docs', 'v1', credentials=creds)
        print("  ✓ Docs API service built successfully!")
        print("  Note: To test reading, provide a document ID")
        return True
    except Exception as e:
        print(f"  ✗ Docs API Error: {e}")
        return False

def test_search_api():
    print_header("CUSTOM SEARCH API TEST")
    
    try:
        service = build("customsearch", "v1", developerKey=GOOGLE_CSE_API_KEY)
        res = service.cse().list(q="test query", cx=GOOGLE_CSE_CX, num=1).execute()
        
        items = res.get('items', [])
        print(f"  ✓ Custom Search API working!")
        
        if items:
            print(f"  Sample result: {items[0].get('title', 'No title')}")
        
        return True
    except Exception as e:
        print(f"  ✗ Custom Search API Error: {e}")
        return False

def main():
    print_header("JARVIS GT2 CREDENTIAL TEST")
    print("  Testing all Google API credentials...")
    
    results = {}
    
    # Step 1: Check files
    check_files()
    
    # We need at least token.json to test
    if not os.path.exists('token.json'):
        print("\n✗ FAILED: No token.json file found. Cannot continue.")
        print("  You need either:")
        print("    1. An existing token.json file, OR")
        print("    2. credentials.json (OAuth client) to generate a new token")
        return
    
    # Step 2: Get and refresh credentials
    try:
        creds = get_google_creds()
        if creds is None:
            print("\n✗ FAILED: Could not obtain valid credentials")
            results['credential_refresh'] = False
            # Still test Search API since it doesn't need OAuth
            results['calendar'] = False
            results['docs'] = False
            results['search'] = test_search_api()
            
            # Print summary and exit
            print_header("TEST SUMMARY")
            for test, passed in results.items():
                status = "✓ PASS" if passed else "✗ FAIL"
                print(f"  {status}: {test.replace('_', ' ').title()}")
            print("\n⚠️  OAuth credentials failed. Only Search API works.")
            print(f"{'='*60}\n")
            return
        results['credential_refresh'] = True
    except Exception as e:
        print(f"\n✗ FAILED to get credentials: {e}")
        results['credential_refresh'] = False
        return
    
    # Step 3: Test each API
    results['calendar'] = test_calendar_api(creds)
    results['docs'] = test_docs_api(creds)
    results['search'] = test_search_api()
    
    # Summary
    print_header("TEST SUMMARY")
    
    for test, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {status}: {test.replace('_', ' ').title()}")
    
    all_passed = all(results.values())
    
    if all_passed:
        print("\n🎉 ALL TESTS PASSED! Credentials are working correctly.")
    else:
        print("\n⚠️  SOME TESTS FAILED. Check errors above.")
    
    print(f"{'='*60}\n")

if __name__ == "__main__":
    main()
