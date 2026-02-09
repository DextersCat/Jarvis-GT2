import requests

# The 5070 Ti Brain Address
BRAIN_URL = "http://192.168.1.27:11434/api/generate"


def test_connection():
    print(f"Connecting to 5070 Ti at {BRAIN_URL}...")
    try:
        payload = {
            "model": "llama3.1:8b", 
            "prompt": "Hello Jarvis, confirm you are running on the RTX 5070 Ti.", 
            "stream": False
        }
        response = requests.post(BRAIN_URL, json=payload, timeout=120)
        
        if response.status_code == 200:
            print("--- RESPONSE FROM BRAIN ---")
            print(response.json()['response'])
            print("---------------------------")
        else:
            print(f"Brain is there but sent an error: {response.status_code}")
            
    except Exception as e:
        print(f"Could not reach the Brain. Check if Ollama is open on the Main PC. Error: {e}")


if __name__ == "__main__":
    test_connection()