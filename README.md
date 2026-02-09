# Jarvis GT2

A sophisticated voice assistant with wake word detection, speech-to-text, text-to-speech, and AI brain integration. Features a Master Profile system for personalized, health-conscious interactions.

## Features

- 🎤 **Wake Word Detection** - "Jarvis" activation using Porcupine
- 🗣️ **Speech-to-Text** - Whisper AI for accurate transcription
- 🔊 **Text-to-Speech** - Piper TTS with custom voice model
- 🛑 **Barge-In Support** - Interrupt Jarvis mid-speech by talking
- 🎙️ **VAD-Based Listening** - Adaptive recording with configurable silence detection
- 🧠 **AI Brain** - Ollama LLM integration (llama3.1:8b)
- 🔍 **Google Integration** - Search, Calendar, Docs, Gmail
- 💬 **Conversation Mode** - Continuous listening with VAD
- 🎮 **Gaming Mode** - Disable mic and free resources
- 📊 **Master Profile** - Personalized communication based on health profile
- 🔔 **n8n Webhook Integration** - Priority notifications
- 💾 **Persistent Memory** - Context retention across sessions

## Modes

1. **Normal Mode** (Default)
   - Listens for "Jarvis" wake word
   - Responds to commands
   - Auto-starts on launch

2. **Gaming Mode**
   - Completely disables microphone
   - Frees all audio resources
   - Safe for gaming/streaming

3. **Conversation Mode**
   - Open mic with Voice Activity Detection
   - No wake word needed
   - Continuous natural conversation

## Setup

### Prerequisites

- Python 3.11+
- Piper TTS installed ([Download](https://github.com/rhasspy/piper/releases))
- Ollama running locally or on network
- Google Cloud credentials (for API access)
- Porcupine access key

### Installation

1. Clone the repository:
```bash
git clone https://github.com/DextersCat/Jarvis-GT2.git
cd Jarvis-GT2
```

2. Create virtual environment:
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

3. Install dependencies:
```bash
pip install customtkinter pvporcupine pvrecorder openai-whisper numpy google-api-python-client google-auth-httplib2 google-auth-oauthlib flask
```

4. Download Piper voice model:
   - Download `jarvis-high.onnx` and `jarvis-high.onnx.json` from Piper releases
   - Place in project directory

5. Configure credentials:
```bash
cp config.template.json config.json
# Edit config.json with your API keys
```

6. Set up Google credentials:
   - Create `credentials.json` from Google Cloud Console
   - Run the app once to generate `token.json`

### Configuration

Edit `config.json` with your credentials:

```json
{
  "picovoice_key": "YOUR_PICOVOICE_KEY",
  "google_client_id": "YOUR_CLIENT_ID",
  "google_client_secret": "YOUR_CLIENT_SECRET",
  "google_cse_api_key": "YOUR_CSE_API_KEY",
  "google_cse_cx": "YOUR_CSE_CX",
  "brain_url": "http://localhost:11434/api/generate",
  "llm_model": "llama3.1:8b",
  "vad_settings": {
    "energy_threshold": 500,
    "silence_duration": 1.2,
    "min_speech_duration": 0.5,
    "barge_in_enabled": true,
    "barge_in_threshold": 800
  }
}
```

#### VAD Settings

- **energy_threshold**: Energy level to detect speech start (default: 500)
- **silence_duration**: Seconds of silence to end speech detection (default: 1.2)
  - Increase if painkillers affect speech pace
- **min_speech_duration**: Minimum speech duration to process (default: 0.5s)
- **barge_in_enabled**: Enable interrupting Jarvis mid-speech (default: true)
- **barge_in_threshold**: Energy level to trigger barge-in (default: 1500)
  - Higher values = less sensitive (won't trigger on keyboard noise)
  - Lower values = more sensitive (easier to interrupt)
  - Typical speech energy: 1500-3000+
  - Keyboard/mouse noise: 800-1200

## Usage

### Quick Start (Windows)

Double-click `start_jarvis.bat` - automatically handles:
- Closing any existing instances
- Activating virtual environment
- Launching Jarvis GT2

Or manually:
```powershell
.\.venv\Scripts\Activate.ps1
python jarvisgt2.py
```

### Stop Jarvis

Double-click `stop_jarvis.bat` or press `Ctrl+C` in the terminal.

### Voice Commands

- "Jarvis, what's the weather?"
- "Jarvis, search for AI news"
- "Jarvis, what's on my calendar?"
- "Jarvis, tell me about Dogzilla" (project memory recall)
- "Jarvis, who are you?" (self-knowledge from memory)

### Barge-In Feature

**Interrupt Jarvis anytime** by simply speaking while he's talking:
- Jarvis monitors the microphone even while speaking
- If you start talking (energy > barge_in_threshold), he stops immediately
- Responds with "Listening, Sir" and waits for your new command
- Fully configurable via `vad_settings` in config.json

This is especially useful for:
- Correcting misunderstood commands
- Stopping long responses
- Low-friction, natural conversation flow

## Master Profile System

Jarvis maintains a persistent memory of your preferences:

- **Working Method**: Research → Propose → Test → Verify
- **Communication Style**: Concise, low-friction
- **Health Profile**: Manages chronic pain and anxiety awareness
- **Break Reminders**: Proactive suggestions every 90 minutes

## n8n Integration

Webhook endpoint: `http://127.0.0.1:5000/jarvis/notify`

Send notifications:
```json
{
  "priority": "URGENT",
  "message": "Meeting in 5 minutes",
  "source": "Calendar"
}
```

## Project Structure

```
├── jarvisgt2.py           # Main application
├── config.json            # Credentials (gitignored)
├── config.template.json   # Configuration template
├── jarvis_memory.json     # Persistent memory storage
├── jarvis-high.onnx       # Piper voice model (download separately)
├── .gitignore            # Git exclusions
└── README.md             # This file
```

## Architecture

- **GUI**: CustomTkinter dark mode interface
- **Wake Word**: Porcupine with "jarvis" keyword
- **STT**: OpenAI Whisper (base model)
- **TTS**: Piper local ONNX model
- **LLM**: Ollama API (llama3.1:8b)
- **Memory**: JSON-based persistence with deque buffer
- **Notifications**: Flask webhook server

## Health & Accessibility

Jarvis includes health-conscious features:
- Concise responses to reduce cognitive load
- Proactive break suggestions
- Health profile integration in communication style
- Low-friction interaction design

## License

MIT License - See LICENSE file for details

## Author

**DextersCat** (Spencer Dixon)
- Email: spencerdixon@btinternet.com
- Location: Kent, UK

## Acknowledgments

- Porcupine by Picovoice
- Whisper by OpenAI
- Piper TTS by Rhasspy
- Ollama for local LLM hosting
