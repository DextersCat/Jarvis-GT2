import requests
import json
import time
import sys

# The URL where Jarvis's webhook listener is running
# This must match the port in jarvis_main.py (default is 5001)
BASE_URL = "http://127.0.0.1:5001"
SPEAK_URL = f"{BASE_URL}/speak"
PING_URL = f"{BASE_URL}/ping"

def test_ping():
    """Tests basic connectivity to the Jarvis webhook server."""
    print(f"-> Pinging Jarvis at {PING_URL}...")
    try:
        response = requests.get(PING_URL, timeout=3)
        if response.status_code == 200 and response.json().get("status") == "pong":
            print("   ✅ SUCCESS: Jarvis is reachable.")
            return True
        else:
            print(f"   ❌ FAILED: Jarvis responded with HTTP {response.status_code}.")
            print(f"      Response: {response.text}")
            return False
    except requests.exceptions.ConnectionError:
        print(f"   ❌ FAILED: Connection to {BASE_URL} refused.")
        print("      This almost always means a FIREWALL is blocking the connection.")
        print("      Please create a rule in Windows Firewall to allow incoming TCP connections on port 5001.")
        return False
    except Exception as e:
        print(f"   ❌ FAILED: An unexpected error occurred during ping: {e}")
        return False
def send_test_email(sender, subject, email_id):
    """Sends a test email payload to the Jarvis webhook."""
    payload = {
        "sender": sender,
        "subject": subject,
        "id": email_id,
        "snippet": "This is a test email to verify the n8n webhook integration."
    }

    print(f"\n-> Sending test email to {SPEAK_URL}...")

    try:
        response = requests.post(SPEAK_URL, json=payload, timeout=5)

        if response.status_code == 200:
            print(f"   ✅ SUCCESS: Jarvis received the email (HTTP 200).")
            print(f"      Response from Jarvis: {response.json()}")
            print("      Check the Jarvis console/dashboard. You should see it being announced or queued.")
        else:
            print(f"   ❌ FAILED: Jarvis returned an error (HTTP {response.status_code}).")
            print(f"      Response: {response.text}")

    except requests.exceptions.ConnectionError:
        print(f"   ❌ FAILED: Connection to {SPEAK_URL} refused.")
        print("      Is Jarvis running? The webhook listener might not be active.")
    except Exception as e:
        print(f"   ❌ FAILED: An unexpected error occurred: {e}")

if __name__ == "__main__":
    print("="*60)
    print("  Jarvis n8n Webhook Integration Test")
    print("="*60)
    print("This script will first ping Jarvis to check connectivity,")
    print("then send a fake email notification.")
    print("\nPlease ensure Jarvis is running before you proceed.")
    input("\nPress Enter to start the test...")

    # Step 1: Test basic connectivity
    if not test_ping():
        print("\n" + "="*60)
        print("Ping test failed. Cannot proceed with email test.")
        print("Please resolve the connection issue above and try again.")
        sys.exit(1)

    # Step 2: Send the test email
    # Generate a unique ID for the test email to avoid deduplication
    unique_id = f"test-email-{int(time.time())}"

    send_test_email(
        sender="Test System <test@jarvis.local>",
        subject="Webhook Integration Test",
        email_id=unique_id
    )

    print("\n" + "="*60)
    print("Test complete.")