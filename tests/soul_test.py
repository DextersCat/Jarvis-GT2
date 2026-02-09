import requests

BRAIN_URL = "http://192.168.1.27:11434/api/generate"

# This is the "Soul" - it tells him he is JARVIS and on the 5070 Ti
soul_prompt = "You are JARVIS, a locally hosted AI assistant running on a high-performance 5070 Ti. You are helping Spencer with his robotics projects. Acknowledge your hardware and greet him."

payload = {
    "model": "llama3.1:8b",
    "prompt": soul_prompt,
    "stream": False
}

print("Sending soul to the brain...")
response = requests.post(BRAIN_URL, json=payload, timeout=60)
print(f"JARVIS: {response.json()['response']}")