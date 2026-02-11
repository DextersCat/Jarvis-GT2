import customtkinter as ctk
import pvporcupine
from pvrecorder import PvRecorder
import threading
import time
import os
import json

# Use OpenVINO-accelerated Whisper
try:
    import whisper
except ImportError:
    print("ERROR: openvino-whisper is not installed. Please run 'pip install openvino-whisper'.")
    sys.exit(1)

import requests
import functools
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
import subprocess
import sys
import logging

try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BeautifulSoup = None
    BS4_AVAILABLE = False

import traceback
import signal
import tempfile
import shutil
import wave
import numpy as np
import collections
import re
from flask import Flask, request, jsonify
from datetime import datetime, timedelta
from dataclasses import dataclass, field

# Add project root to Python path to resolve local modules like 'core'
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)
from vault_reference import VaultReference
from memory_index import MemoryIndex
from dashboard_bridge import DashboardBridge
from core.context_manager import ShortKeyGenerator, SessionContext as NewSessionContext, ConversationalLedger

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not installed, continue with os.getenv

# Location Configuration
LOCATION_OVERRIDE = "Kent,UK"
LATITUDE = 51.172096
LONGITUDE = 0.498793

# Define what Jarvis is allowed to do
SCOPES = [
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/documents',
    'https://www.googleapis.com/auth/drive.file',
    'https://www.googleapis.com/auth/spreadsheets'
]

def check_credentials():
    """
    Check for required credential files and log warnings if missing.
    """
    missing_files = []
    
    if not os.path.exists('credentials.json'):
        missing_files.append('credentials.json')
    
    if not os.path.exists('token.json'):
        missing_files.append('token.json')
    
    if missing_files:
        print("\n" + "="*60)
        print("WARNING: MISSING CREDENTIAL FILES")
        print("="*60)
        for file in missing_files:
            print(f"  ✗ {file} not found in current directory")
        print("\nGoogle API integration will fail without these files.")
        print("Please ensure credentials.json and token.json are present.")
        print("="*60 + "\n")
        return False
    else:
        print("✓ Credentials check passed: credentials.json and token.json found.")
        return True

def get_google_creds():
    creds = None
    # The file token.json stores the user's access and refresh tokens
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # This looks for your 'credentials.json' (the one with Client ID/Secret)
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return creds



# --- CONFIGURATION ---
# Load configuration from config.json with .env overrides
def load_config():
    """Load config from config.json with environment variable overrides.
    Environment variables (.env) take priority for secrets.
    If config.json doesn't exist, all values must come from .env.
    """
    config = {}
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
    except FileNotFoundError:
        print("INFO: config.json not found - using .env only")
    except json.JSONDecodeError as e:
        print(f"ERROR: Invalid JSON in config.json: {e}")
        sys.exit(1)
    
    # Load secrets from environment variables (.env) with fallback to config.json
    picovoice_key = os.getenv("PICOVOICE_KEY") or config.get("picovoice_key")
    google_client_id = os.getenv("GOOGLE_CLIENT_ID") or config.get("google_client_id")
    google_client_secret = os.getenv("GOOGLE_CLIENT_SECRET") or config.get("google_client_secret")
    google_project_id = os.getenv("GOOGLE_PROJECT_ID") or config.get("google_project_id")
    google_cse_api_key = os.getenv("GOOGLE_CSE_API_KEY") or config.get("google_cse_api_key")
    google_cse_cx = os.getenv("GOOGLE_CSE_CX") or config.get("google_cse_cx")
    google_drive_folder_id = os.getenv("GOOGLE_DRIVE_FOLDER_ID") or config.get("google_drive_folder_id")
    google_drive_folder_source_doc_id = os.getenv("GOOGLE_DRIVE_FOLDER_SOURCE_DOC_ID") or config.get("google_drive_folder_source_doc_id")
    owner_email = os.getenv("OWNER_EMAIL") or config.get("owner_email")
    brain_url = os.getenv("BRAIN_URL") or config.get("brain_url", "http://localhost:11434/api/generate")
    llm_model = os.getenv("LLM_MODEL") or config.get("llm_model", "llama3.1:8b")
    piper_exe = os.getenv("PIPER_EXE") or config.get("piper_exe")
    perplexity_api_key = os.getenv("PERPLEXITY_API_KEY") or config.get("perplexity_api_key")
    
    # VAD Settings for barge-in and adaptive listening
    # Environment variables take priority over config.json
    config_vad = config.get("vad_settings", {})
    vad_settings = {
        "energy_threshold": int(os.getenv("VAD_ENERGY_THRESHOLD", config_vad.get("energy_threshold", 500))),
        "silence_duration": float(os.getenv("VAD_SILENCE_DURATION", config_vad.get("silence_duration", 1.2))),
        "min_speech_duration": float(os.getenv("VAD_MIN_SPEECH_DURATION", config_vad.get("min_speech_duration", 0.5))),
        "mic_gain": float(os.getenv("MIC_GAIN", config_vad.get("mic_gain", 1.25))),
        "barge_in_enabled": os.getenv("VAD_BARGE_IN_ENABLED", str(config_vad.get("barge_in_enabled", False))).lower() == "true",
        "barge_in_threshold": int(os.getenv("VAD_BARGE_IN_THRESHOLD", config_vad.get("barge_in_threshold", 1500))),
        "barge_in_delay": float(os.getenv("VAD_BARGE_IN_DELAY", config_vad.get("barge_in_delay", 1.0)))
    }
    
    return {
        "picovoice_key": picovoice_key,
        "google_client_id": google_client_id,
        "google_client_secret": google_client_secret,
        "google_project_id": google_project_id,
        "google_cse_api_key": google_cse_api_key,
        "google_cse_cx": google_cse_cx,
        "google_drive_folder_id": google_drive_folder_id,
        "google_drive_folder_source_doc_id": google_drive_folder_source_doc_id,
        "owner_email": owner_email,
        "brain_url": brain_url,
        "llm_model": llm_model,
        "piper_exe": piper_exe,
        "perplexity_api_key": perplexity_api_key,
        "vad_settings": vad_settings
    }

# Load configuration
config_dict = load_config()
PICOVOICE_KEY = config_dict["picovoice_key"]
GOOGLE_CLIENT_ID = config_dict["google_client_id"]
GOOGLE_CLIENT_SECRET = config_dict["google_client_secret"]
GOOGLE_PROJECT_ID = config_dict["google_project_id"]
GOOGLE_CSE_API_KEY = config_dict["google_cse_api_key"]
GOOGLE_CSE_CX = config_dict["google_cse_cx"]
GOOGLE_DRIVE_FOLDER_ID = config_dict["google_drive_folder_id"]
GOOGLE_DRIVE_FOLDER_SOURCE_DOC_ID = config_dict["google_drive_folder_source_doc_id"]
OWNER_EMAIL = config_dict["owner_email"]
BRAIN_URL = config_dict["brain_url"]
PERPLEXITY_API_KEY = config_dict.get("perplexity_api_key")
LLM_MODEL = config_dict["llm_model"]
VAD_SETTINGS = config_dict["vad_settings"]

# Configure logging — console at INFO, rotating file at DEBUG
from logging.handlers import RotatingFileHandler as _RotatingFileHandler

_log_fmt = logging.Formatter('[%(asctime)s] %(levelname)s %(name)s: %(message)s', datefmt='%H:%M:%S')

_console_handler = logging.StreamHandler()
_console_handler.setLevel(logging.INFO)
_console_handler.setFormatter(_log_fmt)

_file_handler = _RotatingFileHandler(
    'jarvis.log', maxBytes=5 * 1024 * 1024, backupCount=3, encoding='utf-8')
_file_handler.setLevel(logging.DEBUG)
_file_handler.setFormatter(_log_fmt)

logging.root.setLevel(logging.DEBUG)
logging.root.addHandler(_console_handler)
logging.root.addHandler(_file_handler)

logger = logging.getLogger(__name__)

# Topic anchor nouns — used by memory deduplication to identify a fact's subject.
# Two facts sharing ≥1 anchor noun are treated as being about the same topic.
_MEMORY_ANCHORS: frozenset = frozenset({
    'car', 'vehicle', 'van', 'truck', 'bike', 'motorcycle', 'scooter', 'transport',
    'job', 'work', 'role', 'company', 'employer', 'career', 'profession', 'salary',
    'occupation', 'business', 'office', 'client',
    'home', 'address', 'location', 'house', 'flat', 'apartment', 'town', 'city',
    'country', 'street', 'postcode', 'moved',
    'dog', 'cat', 'pet', 'fish', 'bird', 'animal', 'rabbit', 'hamster',
    'wife', 'husband', 'partner', 'girlfriend', 'boyfriend', 'spouse',
    'family', 'children', 'kids', 'son', 'daughter', 'parents', 'brother', 'sister',
    'health', 'pain', 'anxiety', 'medication', 'condition', 'illness',
    'depression', 'stress', 'therapy', 'diagnosis',
    'hobby', 'hobbies', 'passion', 'interest', 'sport', 'music', 'gaming',
    'phone', 'email', 'number', 'contact',
    'diet', 'food', 'eating', 'vegan', 'vegetarian',
    'drink', 'alcohol', 'coffee', 'tea',
    'sleep', 'routine', 'schedule', 'habit',
})

# --- INTENT DEFINITIONS ---
# The new score-based intent router uses these definitions.
# More specific intents should have higher-scoring keywords or 'required' words.
INTENTS = {
    "LEARN_FACT": {
        "keywords": ["remember that", "note that", "update your memory", "store that", "forget that", "no longer true", "correction:", "update:", "note:", "that's wrong"],
        "handler": "handle_learn_fact", "name": "update my memory"
    },
    "SELF_KNOWLEDGE": {
        "keywords": ["who are you", "what do you know about me", "tell me about yourself"],
        "handler": "handle_self_knowledge", "name": "ask about you or me"
    },
    "PROJECT_DOGZILLA": {"keywords": ["dogzilla"], "handler": "handle_dogzilla", "name": "ask about project Dogzilla"},
    "WEATHER": {"keywords": ["weather"], "handler": "handle_weather", "name": "check the weather"},
    "TASK": {
        "keywords": ["remind me", "reminder", "add to my list", "add a task", "don't forget", "note to self", "remember to", "what's on my list", "my tasks", "show tasks", "list tasks", "what do i need to do", "done", "complete", "finished", "mark"],
        "handler": "handle_task_request", "name": "manage my tasks"
    },
    "MEMORY_RECALL": {
        "regex": r'\b(?:did|have)\s+(?:i|you|we)\s+(?:ever\s+)?\w',
        "handler": "handle_task_request", "name": "recall a past action"
    },
    "CALENDAR_READ": {
        "keywords": ["calendar", "what's my day", "diary", "upcoming", "schedule today", "what do i have", "what have i got"],
        "blockers": ["book", "schedule a", "add", "create", "move", "reschedule", "cancel"],
        "handler": "handle_calendar_read", "name": "check my calendar"
    },
    "CALENDAR_ACTION": {
        "keywords": ["book", "cancel", "reschedule", "move", "create an event", "add an event", "schedule a meeting", "schedule a call"],
        "handler": "handle_calendar_action", "name": "change my calendar"
    },
    "REPORT_RETRIEVAL": {
        "keywords": ["report", "optimization", "document", "summary"],
        "required": ["last", "latest", "recent"],
        "handler": "handle_report_retrieval", "name": "get the last report"
    },
    "CODE_OPTIMIZATION": {
        "keywords": ["analys", "optimise", "optimize", "summary", "report"],
        "patterns": [r"\banalys[ez]\b", r"\boptimis[ez]\b"],
        "required": ["file", "code", "script"],
        "handler": "handle_optimization_request", "name": "analyze a file"
    },
    "FILE_COMPARISON": {"keywords": ["compare", "comparison"], "handler": "handle_comparison_request", "name": "compare two files"},
    "EMAIL_SUMMARY": {
        "keywords": ["summarize", "summary", "read", "show"],
        "patterns": [r"\bsummari[sz]e\b", r"\bemail summary\b"],
        "required": ["email", "emails", "mail"],
        "handler": "handle_email_summary_request", "name": "summarize my emails"
    },
    "EMAIL_SEARCH": {
        "keywords": ["search", "find", "look for"],
        "required": ["email", "emails", "mail from", "message from"],
        "handler": "handle_email_search_request", "name": "search my emails"
    },
    "EMAIL_REPLY": {
        "keywords": ["reply", "respond", "answer"],
        "required": ["email", "mail", "last message"],
        "handler": "handle_email_reply_request", "name": "reply to an email"
    },
    "EMAIL_MANAGEMENT": {
        "keywords": ["archive", "bin it", "trash it", "delete that email", "mark handled", "mark as read"],
        "handler": "handle_email_management_request", "name": "manage an email"
    },
    "WEB_SEARCH": {"keywords": ["search", "who is", "what is", "find", "google"], "handler": "handle_web_search", "name": "search the web"}
}

class JarvisGT2:
    def __init__(self):
        # Remove Tkinter GUI initialization - now headless with Cyber-Grid Dashboard
        # All UI handled by: http://localhost:5000
        
        # Create dummy status_var for compatibility (Tkinter removed)
        class DummyVar:
            def set(self, value): pass
        self.status_var = DummyVar()

        self.is_listening = False
        self.gaming_mode = False
        self.conversation_mode = False
        self.mic_muted = False
        self.last_interaction_time = time.time()
        
        # --- NEW: OpenVINO Whisper Integration ---
        logger.info("Loading Whisper STT model...")
        # FINAL FIX: Use "AUTO". This lets the OpenVINO backend select the best
        # hardware (prioritizing NPU) without causing PyTorch device string errors.
        # FALLBACK: Reverting to CPU due to NPU/OpenVINO environment issues.
        self.stt_model = whisper.load_model("base", device="cpu")
        logger.info(f"✓ Whisper STT model offloaded to: {self.stt_model.device}")
        
        self.porcupine = None
        self.recorder = None
        self.wake_word_thread = None
        self.piper_available = self.check_piper_installation()
        self.yes_audio_path = "yes.wav"
        self.generate_yes_audio()
        
        # Short-term context buffer (last 5 exchanges)
        self.context_buffer = collections.deque(maxlen=5)
        
        # Long-term persistent memory
        self.memory_file = "jarvis_memory.json"
        self.memory = self.load_memory()
        
        # Indexed memory system for unlimited action history
        self.memory_index = MemoryIndex(memory_file=self.memory_file)
        
        # --- NEW: Visual Addressing & Context System ---
        self.short_key_generator = ShortKeyGenerator()
        self.session_context = NewSessionContext()
        self.conversational_ledger = ConversationalLedger(self.memory_index, self.short_key_generator)
        
        # Priority Notification Queue (n8n Integration)
        self.notification_queue = []
        self.urgent_interrupt = False
        self.notification_cooldown = 10  # seconds
        self.last_notification_speak_time = 0
        self.awaiting_command = False
        self.notification_hold = False
        self.command_capture_started_at = 0.0
        self.command_capture_timeout = 15.0
        
        # Email deduplication (track seen email IDs for 1 hour)
        self.seen_email_ids = {}  # {email_id: timestamp}
        self.last_email_cleanup = time.time()
        
        # Audio synchronization (prevent speaking over self)
        self.speak_lock = threading.Lock()
        self.queue_lock = threading.Lock()

        # Pending email reply (awaiting confirmation before send)
        self.pending_reply = None  # {email_id, sender, sender_name, reply_text}

        # Intent context tracking (for conversational follow-ups)
        self.last_intent = None  # "email", "calendar", "task", "search", "optimization"
        self.last_calendar_events = []  # [{index, id, summary, start, start_dt}, ...]
        self.last_email_context = None  # For legacy context ("reply to that")
        self.pending_calendar_title = None  # Partial calendar entry awaiting time

        # Task / Reminder system
        self.tasks = []  # Populated after memory loads below

        # Health tracking for proactive interventions
        self.interaction_count = 0
        self.last_break_time = time.time()
        self.memory = self.load_memory()
        
        # VAD parameters - loaded from config
        self.vad_threshold = VAD_SETTINGS.get("energy_threshold", 500)
        self.silence_duration = VAD_SETTINGS.get("silence_duration", 1.2)
        self.min_speech_duration = VAD_SETTINGS.get("min_speech_duration", 0.5)
        self.mic_gain = VAD_SETTINGS.get("mic_gain", 1.25)
        self.barge_in_enabled = VAD_SETTINGS.get("barge_in_enabled", True)
        self.barge_in_threshold = VAD_SETTINGS.get("barge_in_threshold", 800)
        self.barge_in_delay = VAD_SETTINGS.get("barge_in_delay", 1.0)
        
        # Barge-in control flags
        self.is_speaking = False
        self.interrupt_requested = False
        self.vad_monitor_thread = None
        self.vad_monitor_active = False
        self.current_tts_process = None
        
        # Project Vault Configuration
        self.vault_root = r'C:\Users\spencer\Documents\Projects'
        self.active_project = 'New_Jarvis'  # Default project
        self.available_projects = []  # Will be populated on first scan
        self.scan_vault_projects()  # Initialize project list
        
        # Initialize Vault Reference System
        self.vault = VaultReference()
        if self.vault.is_loaded:
            logger.info("✓ Vault index loaded - file reference system active")
            self.log("✓ Vault reference system active")
        else:
            logger.warning("⚠ Vault index not available - file searches may be limited")
            self.log("⚠ Vault index not loaded - generate with: python create_vault_index.py")
        
        # Initialize Dashboard Bridge
        self.dashboard = DashboardBridge()
        self.dashboard.on_health_update = self.handle_health_update
        self.dashboard.on_state_change = self.handle_dashboard_state_change
        self.dashboard.start()
        
        logger.info("Jarvis GT2 initializing...")
        logger.info("🌐 UI handled by Cyber-Grid Dashboard at http://localhost:5000") 
        logger.info("🔊 Running in HEADLESS mode - no Tkinter GUI")
        logger.info("System initialized successfully")
        
        # Initialize n8n webhook listener for priority notifications
        self.setup_n8n_webhook()
        
        # Load tasks from persistent memory (must be after self.memory is loaded)
        self.tasks = self.memory.get("tasks", [])

        # Start reminder scheduler background thread
        self.reminder_thread = threading.Thread(target=self.reminder_scheduler_loop, daemon=True)
        self.reminder_thread.start()

        # Auto-start listening for wake word (Normal Mode)
        self.start_listening()

    def start_listening(self):
        """Start wake word detection automatically."""
        if not self.gaming_mode and not self.is_listening:
            self.log("🎤 Starting wake word detection...")
            logger.info("Auto-starting wake word detection (Normal Mode)")
            self.is_listening = True
            self.wake_word_thread = threading.Thread(target=self.run_wake_word_loop, daemon=True)
            self.wake_word_thread.start()
            logger.debug("Wake word loop thread started")

    def on_closing(self):
        """Handle window close event gracefully."""
        logger.info("Window close requested - shutting down...")
        self.log("Shutting down Jarvis...")
        
        # Stop dashboard bridge
        if hasattr(self, 'dashboard'):
            self.dashboard.push_state(mode="idle")  # Set to idle before shutdown
            self.dashboard.stop()
        
        # Stop listening
        self.is_listening = False
        self.gaming_mode = True  # Force stop all audio
        
        # Clean up resources
        self.cleanup_audio_resources()
        
        # Give threads time to finish
        time.sleep(0.5)
        
        logger.info("Shutdown complete")
        self.destroy()

    def log(self, text):
        """Log to system logger and dashboard (headless mode)."""
        logger.info(text)
        
        # Push to dashboard
        if hasattr(self, 'dashboard'):
            # Map log types
            level = "info"
            upper_text = text.upper()

            # AI responses are 'speak' level, not 'error', even if they contain "error"
            if "JARVIS:" in upper_text:
                level = "speak"
            elif "❌" in text or "ERROR" in upper_text or "FAILED" in upper_text:
                level = "error"
            elif "⚠" in text or "WARN" in upper_text:
                level = "warn"
            elif "LISTENING" in upper_text or "WAKE WORD" in upper_text:
                level = "listen"
            elif "TRANSCRIB" in upper_text or "PROCESS" in upper_text or "ANALYZ" in upper_text:
                level = "process"
            elif "SPEAK" in upper_text or "TTS" in upper_text:
                level = "speak"
            elif "✓" in text or "SUCCESS" in upper_text or "COMPLETE" in upper_text:
                level = "success"
            
            self.dashboard.push_log(level, text)
    
    def load_memory(self):
        """Load persistent memory from jarvis_memory.json."""
        default_memory = {
            "master_location": LOCATION_OVERRIDE,
            "master_coordinates": {"latitude": LATITUDE, "longitude": LONGITUDE},
            "master_profile": {
                "name": "Spencer",
                "working_method": "Research → Propose → Test → Verify",
                "communication_style": "Concise, low-friction, health-conscious",
                "health_profile": {
                    "chronic_pain": True,
                    "anxiety": True,
                    "stress_prone": True,
                    "depression_prone": True,
                    "recommended_break_interval": 90  # minutes
                }
            },
            "facts": [
                "I serve Spencer from Kent, UK",
                "My location is Kent with coordinates 51.172096, 0.498793",
                "I use Ollama with llama3.1:8b as my brain",
                "I can search the web and access Google services",
                "Spencer works using: Research → Propose → Test → Verify method",
                "Spencer manages chronic pain and anxiety"
            ],
            "projects": {
                "dogzilla": {
                    "name": "Dogzilla",
                    "type": "ESP32-based robotics project",
                    "description": "Mobile robotics platform using ESP32 microcontroller",
                    "status": "Active Development",
                    "components": ["ESP32 microcontroller", "Motor drivers", "Sensors", "Custom firmware"]
                }
            },
            "conversation_history": [],
            "last_break_time": None,
            "interaction_count": 0
        }
        
        if os.path.exists(self.memory_file):
            try:
                with open(self.memory_file, 'r') as f:
                    memory = json.load(f)
                    logger.info("✓ Memory loaded from disk")
                    return memory
            except Exception as e:
                logger.warning(f"Failed to load memory: {e}, using defaults")
                return default_memory
        else:
            logger.info("Creating new memory file...")
            self.save_memory(default_memory)
            return default_memory
    
    def save_memory(self, memory=None):
        """Save persistent memory to jarvis_memory.json using indexed system."""
        if memory is None:
            memory = self.memory
        try:
            # Save through memory index (handles vault_actions automatically)
            self.memory_index.save(memory)
            logger.info("✓ Memory saved to disk")
        except Exception as e:
            logger.error(f"Failed to save memory: {e}")
    
    def handle_health_update(self, metric_type: str, level: int):
        """Handle health updates from dashboard (mood/pain tracker).
        
        Args:
            metric_type: "pain" or "anxiety"
            level: 0-4 (None, Mild, Moderate, Severe, Extreme)
        """
        level_names = ["None", "Mild", "Moderate", "Severe", "Extreme"]
        level_name = level_names[level] if 0 <= level < len(level_names) else "Unknown"
        
        # Log to memory
        health_record = {
            "timestamp": datetime.now().isoformat(),
            "type": metric_type,
            "level": level,
            "level_name": level_name
        }

        # Persist to health log file
        health_dir = os.path.join(os.path.dirname(__file__), "health")
        os.makedirs(health_dir, exist_ok=True)
        health_log_path = os.path.join(health_dir, "health_log.jsonl")
        health_snapshot_path = os.path.join(health_dir, "health_snapshot.json")
        try:
            with open(health_log_path, "a", encoding="utf-8") as log_file:
                log_file.write(json.dumps(health_record) + "\n")

            snapshot = {}
            if os.path.exists(health_snapshot_path):
                with open(health_snapshot_path, "r", encoding="utf-8") as snapshot_file:
                    snapshot = json.load(snapshot_file) or {}

            snapshot[metric_type] = {
                "level": level,
                "level_name": level_name,
                "timestamp": health_record["timestamp"]
            }
            with open(health_snapshot_path, "w", encoding="utf-8") as snapshot_file:
                json.dump(snapshot, snapshot_file, indent=2)
        except Exception as e:
            logger.error(f"Failed to write health log: {e}")
        
        # Store in memory
        if "health_logs" not in self.memory:
            self.memory["health_logs"] = []
        self.memory["health_logs"].append(health_record)
        self.save_memory()
        
        self.log(f"📊 Health logged: {metric_type.title()} = {level_name}")
        
        # If pain > 3 (Severe), respond with concern
        if metric_type == "pain" and level > 3:
            response = "I've logged your pain level, Sir. I will keep our responses concise to save your energy."
            self.log(f"Jarvis: {response}")
            self.speak_with_piper(response)
    
    def handle_dashboard_state_change(self, key: str, value: bool):
        """Handle state changes from dashboard UI toggles.
        
        Args:
            key: State key - "gamingMode", "muteMic", or "conversationalMode"
            value: New boolean value
        """
        if key == "gamingMode":
            self.gaming_mode = value
            if value:
                self.log("🎮 Gaming Mode: ENABLED")
                self.log("   → Mic disabled, resources freed")
                logger.info("Gaming mode activated - stopping all listening and freeing resources")
                self.is_listening = False
                # Update dashboard
                self.dashboard.push_state(mode="idle")
            else:
                self.log("🎮 Gaming Mode: DISABLED")
                self.log("   → Resuming normal operation")
                logger.info("Gaming mode deactivated - resuming normal operation")
                self.start_listening()
                
        elif key == "muteMic":
            self.mic_muted = value
            if value:
                self.log("🔇 Microphone: MUTED")
                logger.info("Microphone muted - audio input will be ignored")
            else:
                self.log("🔊 Microphone: UNMUTED")
                logger.info("Microphone unmuted - audio input active")
            self.dashboard.push_state(muteMic=value)
                
        elif key == "conversationalMode":
            self.conversation_mode = value
            if value:
                self.log("💬 Conversation Mode: ENABLED")
                self.log("   → Open mic, natural dialogue")
                if not self.is_listening:
                    self.start_listening()
            else:
                self.log("💬 Conversation Mode: DISABLED")
                self.log("   → Now requires wake word")
                self.conversation_mode = False
            self.dashboard.push_state(conversationalMode=value)
    
    
    def get_file_content(self, reference_name):
        """
        Resolve a file reference (like 'main file') to its path and read content.
        Uses the Vault Index to understand common references.
        
        Args:
            reference_name: User's reference like 'main', 'config', 'startup', etc.
        
        Returns:
            Dictionary with file path and content, or None if not found
        """
        if not self.vault or not self.vault.is_loaded:
            logger.warning("Vault not loaded - cannot resolve file reference")
            return None
        
        try:
            # Try to find the file using vault reference
            file_path = self.vault.get_file(reference_name.lower())
            
            if not file_path:
                # Try exact filename search
                file_path = self.vault.search_file(reference_name)
            
            if not file_path or not os.path.exists(file_path):
                logger.warning(f"File not found for reference: {reference_name}")
                return None
            
            # Read the file content
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            logger.info(f"✓ Read file: {file_path} ({len(content)} bytes)")
            
            # Log file read action to memory
            self.log_vault_action(
                action_type="file_read",
                description=f"Read file: {os.path.basename(file_path)}",
                metadata={
                    "file_path": file_path,
                    "file_size": len(content),
                    "reference": reference_name
                }
            )
            
            return {
                'path': file_path,
                'filename': os.path.basename(file_path),
                'content': content,
                'size': len(content)
            }
            
        except Exception as e:
            logger.error(f"Error reading file: {e}")
            return None
    
    def write_optimization_to_doc(self, filename, report_content):
        """
        Scribe Capability: Write optimization report to Google Doc.
        
        Creates a formatted Google Doc with code analysis/optimization report.
        Automatically saves to configured GOOGLE_DRIVE_FOLDER_ID.
        
        Args:
            filename: Name of the file being analyzed
            report_content: AI-generated analysis/optimization report text
        
        Returns:
            Dictionary with doc_url, doc_id, filename, or None if failed
        """
        doc_title = f"Code Optimization Report - {filename} ({datetime.now().strftime('%Y-%m-%d %H:%M')})"
        
        return self.create_optimization_doc(
            title=doc_title,
            content=report_content,
            folder_id=GOOGLE_DRIVE_FOLDER_ID  # Explicit folder targeting
        )
    
    def resolve_drive_folder_id(self, drive_service, source_doc_id):
        """Resolve a folder ID by reading the parent of a known document."""
        if not source_doc_id:
            return None
        try:
            file_info = drive_service.files().get(
                fileId=source_doc_id,
                fields="parents"
            ).execute()
            parents = file_info.get("parents", [])
            folder_id = parents[0] if parents else None
            if folder_id:
                logger.info(f"✓ Resolved Drive folder ID from source doc: {folder_id}")
            return folder_id
        except Exception as e:
            logger.warning(f"Could not resolve Drive folder ID from source doc: {e}")
            return None
    
    def create_optimization_doc(self, title, content, folder_id=None):
        """
        Create a new Google Doc with optimization analysis or code review.
        Uses Google Docs API to create and write content.
        
        Args:
            title: Title of the document
            content: The text/analysis to write to the document
            folder_id: Optional Google Drive folder ID (uses config value if not provided)
        
        Returns:
            Dictionary with document URL and ID, or None if failed
        """
        try:
            if folder_id is None:
                folder_id = GOOGLE_DRIVE_FOLDER_ID
            
            # Get Google API credentials
            creds = get_google_creds()
            
            if not creds:
                logger.error("Failed to get Google credentials for Docs API")
                return None
            
            # Create Docs service
            docs_service = build('docs', 'v1', credentials=creds)
            drive_service = build('drive', 'v3', credentials=creds)
            
            resolved_folder_id = folder_id
            if not resolved_folder_id and GOOGLE_DRIVE_FOLDER_SOURCE_DOC_ID:
                resolved_folder_id = self.resolve_drive_folder_id(
                    drive_service,
                    GOOGLE_DRIVE_FOLDER_SOURCE_DOC_ID
                )
            
            # Create a new document
            doc_body = {
                'title': title
            }
            
            logger.info(f"Creating Google Doc: {title}")
            doc = docs_service.documents().create(body=doc_body).execute()
            doc_id = doc.get('documentId')
            doc_url = f"https://docs.google.com/document/d/{doc_id}/edit"
            
            logger.info(f"✓ Document created: {doc_url}")
            
            # Write content to the document
            if not content:
                content = "(No content provided)"

            # Docs API requires an insertion location
            requests_body = {
                'requests': [
                    {
                        'insertText': {
                            'location': {'index': 1},
                            'text': content
                        }
                    }
                ]
            }
            
            # Execute the writing request
            docs_service.documents().batchUpdate(
                documentId=doc_id,
                body=requests_body
            ).execute()
            
            logger.info(f"✓ Content written to document ({len(content)} bytes)")
            
            # Move document to specified folder if provided
            if resolved_folder_id:
                try:
                    previous_parents = ",".join(
                        drive_service.files().get(
                            fileId=doc_id,
                            fields='parents'
                        ).execute().get('parents', [])
                    )
                    
                    drive_service.files().update(
                        fileId=doc_id,
                        addParents=resolved_folder_id,
                        removeParents=previous_parents,
                        fields='id, parents'
                    ).execute()
                    
                    logger.info(f"✓ Document moved to folder: {resolved_folder_id}")
                except HttpError as e:
                    status = getattr(e.resp, "status", None)
                    if status == 404 and GOOGLE_DRIVE_FOLDER_SOURCE_DOC_ID:
                        fallback_id = self.resolve_drive_folder_id(
                            drive_service,
                            GOOGLE_DRIVE_FOLDER_SOURCE_DOC_ID
                        )
                        if fallback_id and fallback_id != resolved_folder_id:
                            try:
                                drive_service.files().update(
                                    fileId=doc_id,
                                    addParents=fallback_id,
                                    removeParents=previous_parents,
                                    fields='id, parents'
                                ).execute()
                                resolved_folder_id = fallback_id
                                logger.info(f"✓ Document moved to folder: {resolved_folder_id}")
                            except Exception as retry_error:
                                logger.warning(f"Could not move document to fallback folder: {retry_error}")
                        else:
                            logger.warning(f"Could not resolve fallback Drive folder ID: {e}")
                    else:
                        logger.warning(f"Could not move document to folder: {e}")
                except Exception as e:
                    logger.warning(f"Could not move document to folder: {e}")
            
            # Log this action to memory
            self.log_vault_action(
                action_type="doc_created",
                description=f"Created optimization report: {title}",
                metadata={
                    "doc_id": doc_id,
                    "doc_url": doc_url,
                    "title": title,
                    "content_size": len(content)
                }
            )
            
            return {
                'doc_id': doc_id,
                'doc_url': doc_url,
                'title': title,
                'folder_id': resolved_folder_id,
                'success': True
            }
            
        except Exception as e:
            logger.error(f"Error creating Google Doc: {e}", exc_info=True)
            self.log(f"❌ Error creating doc: {e}")
            return None
    
    def log_vault_action(self, action_type, description, metadata=None):
        """
        Log vault-related actions (file reads, doc creation, conversations) to indexed memory.
        Unlimited storage with fast indexed search.
        
        Args:
            action_type: Type of action ('file_read', 'doc_created', 'conversation', etc.)
            description: Human-readable description of the action
            metadata: Optional dictionary with additional details
        """
        try:
            if not hasattr(self, "memory_index") or self.memory_index is None:
                logger.debug("Skipping vault action log: memory_index unavailable")
                return

            # Add to indexed memory system (no limits)
            self.memory_index.add_action(
                action_type=action_type,
                description=description,
                metadata=metadata
            )
            
            # Save to disk
            self.save_memory()
            
            logger.info(f"Vault action logged: {action_type} - {description}")
            
        except Exception as e:
            logger.error(f"Error logging vault action: {e}")
    
    def handle_report_retrieval(self, user_request):
        """
        Retrieve and summarize the last optimization report from memory.
        Uses indexed search for fast retrieval.
        """
        try:
            # Search indexed memory for last doc_created action
            recent_docs = self.memory_index.search_by_type('doc_created', limit=1)
            
            if not recent_docs:
                self.log("❌ No optimization reports found in memory.")
                self.speak_with_piper("I don't have any saved optimization reports in my memory yet.")
                return
            
            last_report = recent_docs[0]
            
            # Extract report details
            metadata = last_report.get('metadata', {})
            doc_id = metadata.get('doc_id')
            doc_url = metadata.get('doc_url', 'Unknown')
            doc_title = metadata.get('title', 'Unknown Report')
            timestamp = last_report.get('timestamp', 'Unknown time')
            
            # Display report info
            self.log(f"📄 Last Report: {doc_title}")
            self.log(f"🕒 Created: {timestamp}")
            self.log(f"🔗 URL: {doc_url}")
            
            # Read the document content from Google Docs
            self.log("📖 Reading document content...")
            self.speak_with_piper("Reading the optimization report now.")
            
            creds = get_google_creds()
            if not creds or not doc_id:
                self.log("❌ Could not access document")
                self.speak_with_piper("I couldn't access the document.")
                return
            
            docs_service = build('docs', 'v1', credentials=creds)
            doc = docs_service.documents().get(documentId=doc_id).execute()
            
            # Extract text content from the document
            doc_content = ""
            for element in doc.get('body', {}).get('content', []):
                if 'paragraph' in element:
                    for text_run in element['paragraph'].get('elements', []):
                        if 'textRun' in text_run:
                            doc_content += text_run['textRun'].get('content', '')
            
            self.log(f"✓ Read {len(doc_content)} characters from document")
            
            # Send to brain for summarization
            self.log("🧠 Analyzing report for summary...")
            self.speak_with_piper("Analyzing the report for you.")
            
            summary_prompt = f"""Provide a concise 3-point executive summary of this code optimization report:

{doc_content}

Format your response as:
1. [First key finding]
2. [Second key finding]
3. [Third key finding]

Keep it brief and actionable."""
            
            response = requests.post(
                BRAIN_URL,
                json={
                    "model": LLM_MODEL,
                    "prompt": summary_prompt,
                    "stream": False
                },
                timeout=60
            )
            
            summary = response.json().get('response', 'Could not generate summary.')
            
            # Display and speak the summary
            self.log("\n📊 SUMMARY:")
            self.log(summary)
            self.speak_with_piper(f"Here's the summary: {summary}")
            
            # Open in browser as well
            import webbrowser
            webbrowser.open(doc_url)
            self.log(f"✓ Opened in browser: {doc_url}")
            
            # Log report retrieval action
            self.log_vault_action(
                action_type="report_retrieved",
                description=f"Retrieved and summarized: {doc_title}",
                metadata={
                    "doc_id": doc_id,
                    "doc_url": doc_url,
                    "doc_title": doc_title,
                    "original_timestamp": timestamp,
                    "summary_length": len(summary)
                }
            )
            
        except Exception as e:
            logger.error(f"Error retrieving report: {e}", exc_info=True)
            self.log(f"❌ Error retrieving report: {e}")
            self.speak_with_piper("I encountered an error retrieving the report.")
    
    def handle_email_summary_request(self):
        """
        Summarize recent emails from Gmail (or n8n notification queue as fallback).
        Prioritizes: Gmail API (most recent) > n8n queue (automated flow)
        """
        try:
            # Try Gmail API first (most current)
            logger.info("Fetching recent emails from Gmail...")
            gmail_emails = self.get_recent_emails(limit=5)
            
            if gmail_emails:
                # Use Gmail emails
                self.log(f"📧 Found {len(gmail_emails)} recent email(s) in Gmail")
                
                # Format for LLM summarization
                email_text = "RECENT EMAILS FROM GMAIL:\n"
                for i, email in enumerate(gmail_emails, 1):
                    email_text += f"{i}. From: {email['sender']}\n"
                    email_text += f"   Subject: {email['subject']}\n"
                    email_text += f"   Preview: {email['snippet'][:150]}\n\n"

                # Populate session context with e* keys for follow-up commands.
                if hasattr(self, "session_context") and self.session_context:
                    self.session_context.clear()
                    for idx, email in enumerate(gmail_emails, 1):
                        sender_name = self.extract_sender_name(email.get('sender', 'Unknown'))
                        ledger_entry = self.conversational_ledger.add_entry(
                            item_type='e',
                            description=f"Email from {sender_name}",
                            metadata={
                                "id": email.get("id"),
                                "sender": email.get("sender"),
                                "subject": email.get("subject"),
                                "snippet": email.get("snippet"),
                            }
                        )
                        full_key = ledger_entry.get('metadata', {}).get('short_key', '')
                        short_alias = f"e{idx}"
                        self.session_context.add_item(
                            full_key=f"{datetime.now().strftime('%Y%m%d')}-{short_alias}",
                            label=sender_name,
                            item_type='e',
                            metadata={
                                "id": email.get("id"),
                                "sender": email.get("sender"),
                                "subject": email.get("subject"),
                                "snippet": email.get("snippet"),
                            }
                        )
            else:
                # Fallback to n8n notification queue
                logger.info("No Gmail emails found, checking n8n queue...")
                
                email_notifications = [
                    n for n in self.notification_queue 
                    if n.get('source') == 'Email'
                ]
                
                if not email_notifications:
                    self.log("❌ No recent emails found")
                    self.speak_with_piper("You don't have any recent emails.")
                    return
                
                # Format n8n notification emails
                email_text = "RECENT EMAILS FROM NOTIFICATIONS:\n"
                for i, email in enumerate(email_notifications[-5:], 1):  # Last 5
                    metadata = email.get('metadata', {})
                    email_text += f"{i}. From: {metadata.get('sender', 'Unknown')}\n"
                    email_text += f"   Subject: {metadata.get('subject', 'No Subject')}\n"
                    email_text += f"   {email.get('message', '')}\n\n"
                
                self.log(f"📧 Found {len(email_notifications)} email(s) in queue")
            
            # Send to brain for summarization
            self.log("🧠 Generating AI summary...")
            self.speak_with_piper("Summarizing your emails now.")
            
            summary_prompt = f"""Provide a brief executive summary of these emails in 2-3 sentences.
Focus on important senders and key topics.

{email_text}

Summary (concise, action-item focused):"""
            
            response = requests.post(
                BRAIN_URL,
                json={
                    "model": LLM_MODEL,
                    "prompt": summary_prompt,
                    "stream": False
                },
                timeout=60
            )
            
            summary = response.json().get('response', 'Could not generate summary.')
            
            # Display and speak the summary
            self.log("\n📧 EMAIL SUMMARY:")
            self.log(summary)
            self.speak_with_piper(f"Here's your email summary: {summary}")
            
            # Push to dashboard
            if hasattr(self, 'dashboard') and gmail_emails:
                focus_content = summary[:300] + "\n\nEmails:\n"
                for alias, entry in list(self.session_context.items.items())[:5]:
                    meta = entry.get("metadata", {})
                    focus_content += f"\n[{alias}] {entry.get('label', 'Unknown')}"
                    focus_content += f"\n  Subject: {meta.get('subject', 'No Subject')}"

                self.dashboard.push_focus(
                    content_type="email",
                    title="Email Summary",
                    content=focus_content
                )
                self.dashboard.update_ticker(self.session_context.get_all_items_for_ticker())
            
            # Log email summary action
            self.log_vault_action(
                action_type="email_summarized",
                description=f"Summarized recent emails",
                metadata={
                    "source": "Gmail API" if gmail_emails else "n8n notifications",
                    "email_count": len(gmail_emails) if gmail_emails else len(email_notifications),
                    "summary_length": len(summary),
                    "timestamp": datetime.now().isoformat()
                }
            )
            
        except Exception as e:
            logger.error(f"Error summarizing emails: {e}", exc_info=True)
            self.log(f"❌ Error summarizing emails: {e}")
            self.speak_with_piper("I encountered an error summarizing your emails.")
    
    def call_smart_model(self, prompt, timeout=120):
        """
        Calls a high-capability model with a fallback to local Ollama.
        The full implementation would try a primary cloud API first.
        For this recovery, we are using the local Ollama brain directly.
        """
        try:
            logger.info("Calling smart model (Ollama)...")
            started_at = time.time()
            resp = requests.post(
                BRAIN_URL,
                json={"model": LLM_MODEL, "prompt": prompt, "stream": False},
                timeout=timeout
            )
            resp.raise_for_status()
            elapsed_ms = int((time.time() - started_at) * 1000)
            if hasattr(self, "dashboard") and self.dashboard:
                self.dashboard.set_last_ollama_response_time(elapsed_ms)
            logger.info("Smart model call successful.")
            return resp.json().get('response', 'Analysis could not be completed.')
        except requests.exceptions.RequestException as e:
            logger.error(f"call_smart_model failed to connect to BRAIN_URL: {e}")
            return f"Error: I was unable to connect to my AI brain at {BRAIN_URL}."
        except Exception as e:
            logger.error(f"call_smart_model encountered an unexpected error: {e}", exc_info=True)
            return f"An unexpected error occurred while I was thinking."

    def handle_email_search_request(self, user_request):
        """
        Search Gmail for emails from a specific person or with subject keywords.
        
        Examples:
        - "Find emails from John"
        - "Search for emails from john@example.com about the proposal"
        - "Look for messages from Sarah"
        """
        try:
            text_lower = user_request.lower()
            
            # Extract sender name/email from request
            # Patterns: "from [name/email]", "from: [name/email]", "[name/email]"
            import re
            
            # Try to extract email pattern
            email_match = re.search(r'([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', user_request)
            sender_query = email_match.group(1) if email_match else None
            
            # Try to extract name after "from"
            if not sender_query:
                from_match = re.search(r'from\s+([a-zA-Z\s]+?)(?:\s+about|\s+regarding|\s+subject|$)', user_request, re.IGNORECASE)
                if from_match:
                    sender_query = from_match.group(1).strip()
            
            if not sender_query:
                self.log("❌ Could not identify who to search for")
                self.speak_with_piper("Could you please specify whose emails you'd like me to search for?")
                return
            
            # Build Gmail search query
            gmail_query = f"from:{sender_query}"
            
            # Check for subject keywords too
            subject_match = re.search(r'(?:about|regarding|subject:)\s+([a-zA-Z\s]+?)(?:$|\s+before|\s+since)', user_request, re.IGNORECASE)
            if subject_match:
                subject = subject_match.group(1).strip()
                gmail_query += f" subject:{subject}"
            
            logger.info(f"Gmail search query: {gmail_query}")
            self.log(f"🔍 Searching Gmail for: {sender_query}")
            self.status_var.set("Status: Searching Gmail...")
            
            # Perform Gmail search
            emails = self.search_emails(gmail_query)
            
            if not emails:
                self.log(f"❌ No emails found from {sender_query}")
                self.speak_with_piper(f"I didn't find any emails from {sender_query}.")
                return
            
            # Format results for display and speaking
            self.log(f"✓ Found {len(emails)} email(s)")
            
            # Prepare summary for user
            if len(emails) == 1:
                email = emails[0]
                summary = f"Found 1 email from {self.extract_sender_name(email['sender'])} with subject: {email['subject']}"
                self.log(f"📧 From: {email['sender']}")
                self.log(f"   Subject: {email['subject']}")
                self.log(f"   Preview: {email['snippet'][:100]}")
            else:
                summary = f"Found {len(emails)} emails from {sender_query}:"
                for i, email in enumerate(emails[:3], 1):  # Show top 3
                    self.log(f"{i}. {email['subject']} - {self.extract_sender_name(email['sender'])}")
            
            # Push to dashboard
            if hasattr(self, 'dashboard'):
                if hasattr(self, "session_context") and self.session_context:
                    self.session_context.clear()
                    for idx, email in enumerate(emails, 1):
                        sender_name = self.extract_sender_name(email.get('sender', 'Unknown'))
                        ledger_entry = self.conversational_ledger.add_entry(
                            item_type='e',
                            description=f"Email search hit from {sender_name}",
                            metadata={
                                "id": email.get("id"),
                                "sender": email.get("sender"),
                                "subject": email.get("subject"),
                                "snippet": email.get("snippet"),
                            }
                        )
                        full_key = ledger_entry.get('metadata', {}).get('short_key', '')
                        short_alias = f"e{idx}"
                        self.session_context.add_item(
                            full_key=f"{datetime.now().strftime('%Y%m%d')}-{short_alias}",
                            label=sender_name,
                            item_type='e',
                            metadata={
                                "id": email.get("id"),
                                "sender": email.get("sender"),
                                "subject": email.get("subject"),
                                "snippet": email.get("snippet"),
                            }
                        )

                cards = []
                for idx, (_alias, entry) in enumerate(list(self.session_context.items.items())[:5], 1):
                    meta = entry.get("metadata", {})
                    subject = meta.get("subject", "No Subject")
                    sender = meta.get("sender", "Unknown")
                    snippet = self._two_sentence_snippet(meta.get("snippet", ""))
                    link = self._email_permalink(meta.get("id"))
                    md_link = f"[Open Link]({link})" if link else "Open Link unavailable"
                    cards.append(
                        f"### [EMAIL {idx}] {subject}\n"
                        f"From: {sender}\n\n"
                        f"{snippet}\n\n"
                        f"{md_link}\n"
                    )
                focus_content = "\n\n".join(cards) if cards else summary[:300]
                
                self.dashboard.push_focus(
                    content_type="email",
                    title=f"Email Search: {sender_query}",
                    content=focus_content
                )
                self.dashboard.update_ticker(self.session_context.get_all_items_for_ticker())
            
            # Speak results
            self.speak_with_piper(summary)
            
            # Log action
            self.log_vault_action(
                action_type="email_searched",
                description=f"Searched emails from: {sender_query}",
                metadata={
                    "search_query": gmail_query,
                    "results_count": len(emails),
                    "timestamp": datetime.now().isoformat()
                }
            )
            
        except Exception as e:
            logger.error(f"Error searching emails: {e}", exc_info=True)
            self.log(f"❌ Email search failed: {e}")
            self.speak_with_piper("I encountered an error searching your emails.")
    
    def handle_email_reply_request(self, user_request):
        """
        Reply to the most recent email or a specific sender's email.
        
        Examples:
        - "Reply to the last email saying thanks"
        - "Reply to John saying I'll send it tomorrow"
        - "Send a reply: I agree with your proposal"
        """
        try:
            text_lower = user_request.lower()
            
            # Extract the reply message after common patterns
            import re
            
            reply_match = re.search(r'(?:saying|with|message:?)\s+(.+?)$', user_request, re.IGNORECASE)
            
            if not reply_match:
                self.log("❌ Could not identify reply message")
                self.speak_with_piper("What would you like me to say in the reply?")
                return
            
            reply_text = reply_match.group(1).strip()
            
            # Get recent emails to find which one to reply to
            logger.info("Fetching recent emails to find reply target...")
            self.status_var.set("Status: Fetching emails...")
            
            recent_emails = self.get_recent_emails(limit=1)
            
            if not recent_emails:
                self.log("❌ No recent emails found to reply to")
                self.speak_with_piper("You don't have any recent emails to reply to.")
                return
            
            # Get the most recent email
            email_to_reply = recent_emails[0]
            email_id = email_to_reply['id']
            sender = email_to_reply['sender']
            
            self.log(f"✉️ Replying to email from {self.extract_sender_name(sender)}")
            self.log(f"   Message: {reply_text[:100]}")
            self.status_var.set("Status: Sending reply...")
            
            # Send the reply
            success = self.reply_to_email(email_id, reply_text)
            
            if success:
                confirmation = f"Reply sent to {self.extract_sender_name(sender)}"
                self.log(f"✓ {confirmation}")
                self.speak_with_piper(confirmation)
                
                # Log action
                self.log_vault_action(
                    action_type="email_replied",
                    description=f"Replied to email from {sender}",
                    metadata={
                        "recipient": sender,
                        "message_preview": reply_text[:100],
                        "timestamp": datetime.now().isoformat()
                    }
                )
            else:
                self.log("❌ Failed to send reply")
                self.speak_with_piper("I had trouble sending that reply.")
            
        except Exception as e:
            logger.error(f"Error replying to email: {e}", exc_info=True)
            self.log(f"❌ Reply failed: {e}")
            self.speak_with_piper("I encountered an error sending your reply.")
    
    def _handle_contextual_command(self, raw_text: str) -> bool:
        """
        Contextual Resolver: Handles commands targeting a short-key (e.g., "open wr1").
        Returns True if a command was found and handled, False otherwise.
        """
        text = raw_text.lower().strip()
        if not hasattr(self, "session_context") or self.session_context is None:
            return False

        def _get_item(alias: str):
            return self.session_context.get_item(alias.lower()) if alias else None

        def _present_item(alias: str, open_web: bool = False) -> bool:
            item = _get_item(alias)
            if not item:
                self.speak_with_piper(f"I couldn't find {alias} in this session.")
                return True

            item_type = item.get('type')
            meta = item.get('metadata', {})
            label = item.get('label', alias)

            if item_type == 'w':
                url = meta.get('url')
                if open_web and url:
                    import webbrowser
                    webbrowser.open(url)
                    self.speak_with_piper(f"Opening {label}.")
                else:
                    content = f"{meta.get('snippet', '')}\n\nURL: {url}"
                    self.dashboard.push_focus("docs", f"[{alias}] {label}", content)
                    self.speak_with_piper(f"Showing {alias}.")
                return True
            if item_type in ('d', 'c'):
                content = meta.get('summary', '(No content stored)')
                self.dashboard.push_focus("docs", f"[{alias}] {label}", content)
                self.speak_with_piper(f"Showing {alias}.")
                return True
            if item_type == 'e':
                content = (
                    f"From: {meta.get('sender', 'Unknown')}\n"
                    f"Subject: {meta.get('subject', 'No Subject')}\n\n"
                    f"{meta.get('snippet', '(No preview available)')}"
                )
                self.dashboard.push_focus("email", f"[{alias}] {label}", content)
                self.speak_with_piper(f"Showing {alias}.")
                return True

            self.speak_with_piper(f"I couldn't display {alias}.")
            return True

        ordinal_map = {
            "one": 1, "first": 1,
            "two": 2, "second": 2,
            "three": 3, "third": 3,
            "four": 4, "fourth": 4,
            "five": 5, "fifth": 5,
            "six": 6, "sixth": 6,
            "seven": 7, "seventh": 7,
            "eight": 8, "eighth": 8,
            "nine": 9, "ninth": 9,
            "ten": 10, "tenth": 10,
            # Common Whisper homophones/mis-hearings
            "for": 4, "to": 2, "too": 2, "won": 1, "ate": 8
        }
        ordinal_tokens_pattern = (
            r"\d+|one|first|two|second|three|third|four|fourth|five|fifth|six|sixth|"
            r"seven|seventh|eight|eighth|nine|ninth|ten|tenth|for|to|too|won|ate"
        )

        def _sorted_aliases(item_type=None):
            aliases = []
            for alias, item in self.session_context.items.items():
                if item_type and item.get("type") != item_type:
                    continue
                aliases.append(alias)
            def _alias_sort_key(a):
                m_num = re.search(r"(\d+)$", a)
                n = int(m_num.group(1)) if m_num else 9999
                return (a[:2], n, a)
            return sorted(aliases, key=_alias_sort_key)

        def _resolve_alias_from_phrase(phrase: str):
            if not phrase:
                return None
            phrase = phrase.strip().lower()

            # Direct short-key support remains first-class.
            direct = re.search(r"\b([a-z]+\d+)\b", phrase)
            if direct:
                return direct.group(1).lower()

            # Natural ordinal support: "web result one", "email 2", "the first result"
            m_nat = re.search(
                rf"\b(?:the\s+)?(web|email|result|code|doc|document|analysis|report)\s*(?:result\s*)?({ordinal_tokens_pattern})\b",
                phrase
            )
            if not m_nat:
                m_nat = re.search(rf"\b(?:the\s+)?({ordinal_tokens_pattern})\s+result\b", phrase)
                if not m_nat:
                    return None
                kind = "result"
                token = m_nat.group(1)
            else:
                kind = m_nat.group(1)
                token = m_nat.group(2)

            if token.isdigit():
                ordinal = int(token)
            else:
                ordinal = ordinal_map.get(token)
            if not ordinal or ordinal < 1:
                return None
            idx = ordinal - 1

            desired_type = None
            if kind == "web":
                desired_type = "w"
            elif kind == "email":
                desired_type = "e"
            elif kind in ("code",):
                desired_type = "c"
            elif kind in ("doc", "document", "analysis", "report"):
                desired_type = "d"
            elif kind == "result":
                if self.last_intent == "search":
                    desired_type = "w"
                elif self.last_intent == "email":
                    desired_type = "e"
                elif self.last_intent == "optimization":
                    desired_type = "c"

            aliases = _sorted_aliases(desired_type)
            if idx >= len(aliases):
                return None
            return aliases[idx]

        # "dig deeper into wr1"
        m = re.search(r'\bdig\s+deeper\s+into\s+([a-z]+\d+)\b', text)
        if m:
            alias = m.group(1).lower()
            return self.handle_deep_dig(alias)
        m = re.search(r'\bdig\s+deeper\s+into\s+(.+)$', text)
        if m:
            alias = _resolve_alias_from_phrase(m.group(1))
            if alias:
                return self.handle_deep_dig(alias)

        # Natural quick deep-dig: "web result 3" / "result one"
        m = re.fullmatch(
            rf'\s*(?:the\s+)?(?:web\s+)?result\s*({ordinal_tokens_pattern})\s*',
            text
        )
        if m:
            alias = _resolve_alias_from_phrase(f"web result {m.group(1)}")
            if alias:
                item = _get_item(alias)
                if item and item.get("type") == "w":
                    return self.handle_deep_dig(alias)

        # "reply to e1 saying ..." or "reply to e1"
        m = re.search(r'\breply\s+to\s+([a-z]+\d+|.+?)(?:\s+(?:saying|with)\s+(.+))?$', raw_text, re.IGNORECASE)
        if m:
            alias = _resolve_alias_from_phrase(m.group(1)) or m.group(1).lower()
            reply_text = (m.group(2) or "").strip()
            item = _get_item(alias)
            if not item or item.get('type') != 'e':
                self.speak_with_piper(f"I couldn't find {alias} in this session.")
                return True
            if not reply_text:
                self.speak_with_piper("What would you like me to say in the reply?")
                return True
            meta = item.get('metadata', {})
            sender_name = self.extract_sender_name(meta.get('sender', item.get('label', 'that sender')))
            self.pending_reply = {
                'email_id': meta.get('id'),
                'sender': meta.get('sender', sender_name),
                'sender_name': sender_name,
                'reply_text': reply_text
            }
            self.dashboard.push_focus(
                "email",
                "Pending Reply - Awaiting Confirmation",
                f"To: {sender_name}\n\nDraft:\n{reply_text}"
            )
            self.speak_with_piper(f"Just to confirm, shall I send that reply to {sender_name}?")
            self.last_intent = "email"
            return True

        # "archive e1" / "delete e1" / "trash e1"
        m = re.search(r'\b(?:archive|delete|trash|bin)\s+([a-z]+\d+|.+)$', text)
        if m:
            alias = _resolve_alias_from_phrase(m.group(1)) or m.group(1).lower()
            item = _get_item(alias)
            if not item or item.get('type') != 'e':
                self.speak_with_piper(f"I couldn't find {alias} in this session.")
                return True
            email_id = item.get('metadata', {}).get('id')
            if any(w in text for w in ['delete', 'trash', 'bin']):
                ok = self.trash_email(email_id)
                msg = f"Done. {alias} moved to trash." if ok else "I had trouble deleting that email."
            else:
                ok = self.archive_email(email_id)
                msg = f"Done. {alias} archived." if ok else "I had trouble archiving that email."
            self.speak_with_piper(msg)
            return True

        # "show e1" / "open wr1" / "show me c1"
        m = re.search(r'\b(?:show|open)(?:\s+me)?\s+([a-z]+\d+|.+)$', text)
        if m:
            alias = _resolve_alias_from_phrase(m.group(1)) or m.group(1).lower()
            return _present_item(alias, open_web=('open' in text))

        # Natural quick-action references:
        # - "web result 3" -> deep dive that web result
        # - "email 2" / "doc 1" / "code 1" / "result 2" -> present item
        m = re.fullmatch(
            rf'\s*(?:the\s+)?(?:web|email|result|code|doc|document|analysis|report)?\s*(?:result\s*)?({ordinal_tokens_pattern})\s*',
            text
        )
        if m:
            alias = _resolve_alias_from_phrase(text)
            if alias:
                item = _get_item(alias)
                if item and item.get("type") == "w":
                    return self.handle_deep_dig(alias)
                return _present_item(alias)

        return False

    def _two_sentence_snippet(self, text: str, max_chars: int = 280) -> str:
        """Return up to two short sentences for focus-card previews."""
        if not text:
            return "No summary snippet available."
        cleaned = " ".join(str(text).split())
        parts = re.split(r'(?<=[.!?])\s+', cleaned)
        snippet = " ".join(parts[:2]).strip()
        if not snippet:
            snippet = cleaned
        if len(snippet) > max_chars:
            snippet = snippet[:max_chars].rstrip() + "..."
        return snippet

    def _email_permalink(self, email_id: str) -> str:
        """Build a direct Gmail permalink when message id is available."""
        if not email_id:
            return ""
        return f"https://mail.google.com/mail/u/0/#inbox/{email_id}"

    def handle_web_search(self, user_request: str):
        """Search the web, store results as wr* session items, and update dashboard."""
        remove_phrases = [
            "search the web for", "search for", "google for", "google",
            "look up", "find out about", "find", "tell me about"
        ]
        query = user_request.lower()
        for phrase in remove_phrases:
            query = query.replace(phrase, "")
        query = query.strip()
        if not query:
            self.speak_with_piper("What would you like me to search for?")
            return

        self.speak_with_piper(f"Searching for {query}.")
        results = self.google_search(query, structured=True)
        if not results:
            self.speak_with_piper("I couldn't find any useful results.")
            return

        if hasattr(self, "session_context") and self.session_context:
            self.session_context.clear()

        cards = []
        summary_seed = []
        for idx, item in enumerate(results[:5], 1):
            title = item.get('title', 'Untitled').split('|')[0].strip()
            snippet = item.get('snippet', '')
            url = item.get('link')
            ledger_entry = self.conversational_ledger.add_entry(
                item_type='w',
                description=f"Web result: {title}",
                metadata={'title': title, 'snippet': snippet, 'url': url}
            )
            full_key = ledger_entry.get('metadata', {}).get('short_key', '')
            short_alias = f"wr{idx}"
            self.session_context.add_item(
                full_key=f"{datetime.now().strftime('%Y%m%d')}-{short_alias}",
                label=title,
                item_type='w',
                metadata={'title': title, 'snippet': snippet, 'url': url}
            )
            md_link = f"[Open Link]({url})" if url else "Open Link unavailable"
            summary_snippet = self._two_sentence_snippet(snippet)
            cards.append(
                f"### [WEB RESULT {idx}] {title}\n"
                f"{summary_snippet}\n\n"
                f"{md_link}\n"
            )
            summary_seed.append(
                f"{idx}. {title}\nSummary Snippet: {summary_snippet}\nURL: {url or 'N/A'}"
            )

        focus_content = "\n\n".join(cards)
        self.dashboard.push_focus("docs", f"Web Results: {query}", focus_content)
        self.dashboard.update_ticker(self.session_context.get_all_items_for_ticker())
        count = len(cards)

        summary_prompt = (
            "You are assisting Spencer (the Master). "
            "Do not just say you found a list. "
            "Provide a 3-bullet point summary of the most important insights from these results "
            "so the Master can decide which one to dig into.\n\n"
            f"Search query: {query}\n\n"
            "Results:\n"
            f"{chr(10).join(summary_seed)}\n\n"
            "Return exactly 3 concise bullets."
        )
        spoken_summary = self.call_smart_model(summary_prompt, timeout=90)
        self.speak(spoken_summary)
        self.last_intent = "search"

    def handle_deep_dig(self, alias: str) -> bool:
        """Analyze a web result referenced by short key (wr*), then store as d*."""
        item = self.session_context.get_item(alias)
        if not item or item.get('type') != 'w':
            self.speak_with_piper(f"I couldn't find {alias} in this session.")
            return True

        url = item.get('metadata', {}).get('url')
        title = item.get('label', alias)
        if not url:
            self.speak_with_piper(f"{alias} does not contain a URL to analyze.")
            return True

        self.speak_with_piper(f"Digging deeper into {title}.")
        try:
            headers = {"User-Agent": "Mozilla/5.0 (compatible; JarvisGT2/1.0)"}
            resp = requests.get(url, timeout=15, headers=headers)
            resp.raise_for_status()
            if not BS4_AVAILABLE or BeautifulSoup is None:
                extracted = resp.text[:5000]
            else:
                soup = BeautifulSoup(resp.text, "html.parser")
                extracted = " ".join(soup.stripped_strings)[:8000]

            prompt = (
                "Summarize the following page content in concise action-oriented bullet points:\n\n"
                f"Title: {title}\nURL: {url}\n\n{extracted}"
            )
            summary = self.call_smart_model(prompt, timeout=90)

            ledger_entry = self.conversational_ledger.add_entry(
                item_type='d',
                description=f"Deep dig analysis for {title}",
                metadata={'source_alias': alias, 'source_url': url, 'summary': summary, 'title': title}
            )
            full_key = ledger_entry.get('metadata', {}).get('short_key', '')
            existing_d = [k for k in self.session_context.items.keys() if k.startswith('d')]
            short_alias = f"d{len(existing_d) + 1}"
            self.session_context.add_item(
                full_key=f"{datetime.now().strftime('%Y%m%d')}-{short_alias}",
                label=f"Analysis: {title}",
                item_type='d',
                metadata={'summary': summary, 'source_url': url, 'source_alias': alias}
            )

            self.dashboard.push_focus("docs", f"Analysis of {alias}: {title}", summary)
            self.dashboard.update_ticker(self.session_context.get_all_items_for_ticker())
            self.speak_with_piper(
                f"Sir, my analysis of {title} is complete and on screen. It is now referenced as {short_alias}."
            )
            self.last_intent = "search"
            return True
        except Exception as e:
            logger.error(f"Deep dig failed: {e}", exc_info=True)
            self.speak_with_piper("I had trouble analyzing that result.")
            return True

    def handle_optimization_request(self, user_request):
        """
        Multi-step intent handler for code analysis and documentation workflow.
        
        Flow:
        1. Confirm the task with the user via VAD
        2. Read the specified file content from vault
        3. Send to Ollama with optimization-focused prompt
        4. Create a Google Doc with the analysis (Scribe Workflow)
        5. Confirm completion with the URL, adding a short-key to the session
        """
        try:
            self.status_var.set("Status: 🔧 Analyzing code...")
            
            # Step 1: Extract which file the user wants to analyze
            text_lower = user_request.lower()
            
            # Try to determine which file to analyze
            target_file = None
            
            # Look for specific file references
            if "main" in text_lower:
                target_file = self.vault.get_file('main')
            elif "startup" in text_lower:
                target_file = self.vault.get_file('startup')
            elif "config" in text_lower:
                target_file = self.vault.get_file('config')
            elif "ear" in text_lower:
                target_file = self.vault.get_file('ear')
            else:
                # Try to extract filename from request
                # Look for patterns like "check [filename]"
                import re
                file_match = re.search(r'(?:check|analyze|optimize|read)\s+(?:the\s+)?(?:file\s+)?([a-zA-Z_]\w*\.py)', text_lower)
                if file_match:
                    filename = file_match.group(1)
                    target_file = self.vault.search_file(filename)
            
            if not target_file:
                self.log("❌ Could not identify which file to analyze. Please specify a file name.")
                self.speak_with_piper("I couldn't identify which file you'd like me to analyze. Please be more specific.")
                return
            
            # Log action
            self.log_vault_action(
                action_type="optimization_start",
                description=f"Starting optimization analysis for {os.path.basename(target_file)}"
            )
            
            # Step 2: Read the file content
            self.log(f"📖 Reading: {os.path.basename(target_file)}")
            self.speak_with_piper("Reading the file now.")
            
            file_data = self.get_file_content(os.path.basename(target_file))
            
            if not file_data or not file_data.get('content'):
                self.log(f"❌ Could not read file: {target_file}")
                self.speak_with_piper("I had trouble reading the file. Please check it exists.")
                return
            
            file_content = file_data['content']
            filename = file_data['filename']
            
            # Step 3: Send to Ollama/Brain for optimization analysis
            self.log("🧠 Sending to AI brain for analysis...")
            self.speak_with_piper("Analyzing the code for optimization opportunities.")
            
            optimization_prompt = f"""You are an expert code reviewer analysing a specific codebase.

ARCHITECTURE (read carefully before analysing):
- This is a headless Python voice assistant — no GUI, no web framework serving users.
- NO SQL database, no SQLAlchemy, no db_session, no User/Conversation ORM models.
- Conversation state is held in self.context_buffer (a Python list already in RAM).
- Persistent memory is jarvis_memory.json — loaded once at startup, saved periodically.
- Flask runs in a single daemon background thread solely to receive n8n webhooks on port 5001.
- Background tasks use threading.Thread(daemon=True) — no thread pool is needed or appropriate.
- There is nothing to cache — all runtime state is already in memory.
DO NOT suggest: databases, SQLAlchemy, ThreadPoolExecutor for Flask.run(), or caching layers.

FILE TO ANALYSE: {filename}

CODE:
{file_content}

Identify the THREE most important real improvements specific to THIS codebase. For each:
1. Issue: Describe the actual problem found in this file
2. Impact: What concrete benefit would this provide?
3. Suggestion: Show a specific code change (not a generic pattern)

Plain text only — no markdown, no bullet symbols, no code fences."""
            
            # Send to brain (Ollama)
            self.status_var.set("Status: 🧠 AI Analysis in Progress...")
            optimization_analysis = self.call_smart_model(optimization_prompt, timeout=120)
            self.log("✓ Analysis complete")
            
            # Step 4: Create Google Doc with the analysis (Scribe Workflow)
            self.log("📝 Creating Google Doc...")
            self.speak_with_piper("Creating your optimization report document.")
            
            # Use write_optimization_to_doc() for clean Scribe workflow
            doc_result = self.write_optimization_to_doc(
                filename=filename,
                report_content=optimization_analysis
            )
            
            if not doc_result or not doc_result.get('success'):
                self.log("❌ Failed to create Google Doc")
                self.speak_with_piper("I encountered an error creating the document.")
                return
            
            doc_url = doc_result.get('doc_url')
            
            # --- NEW: Integrate with Visual Addressing ---
            ledger_entry = self.conversational_ledger.add_entry(
                item_type='c', # 'c' for code/vault analysis
                description=f"Code analysis for {filename}",
                metadata={
                    'doc_id': doc_result.get('doc_id'),
                    'doc_url': doc_result.get('doc_url'),
                    'source_file': filename,
                    'summary': optimization_analysis
                }
            )
            _full_key = ledger_entry['metadata']['short_key']
            existing_c = [k for k in self.session_context.items.keys() if k.startswith('c')]
            new_short_alias = f"c{len(existing_c) + 1}"
            new_full_key = f"{datetime.now().strftime('%Y%m%d')}-{new_short_alias}"

            self.session_context.add_item(
                full_key=new_full_key,
                label=f"Analysis: {filename}",
                item_type='c',
                metadata={
                    'doc_url': doc_result.get('doc_url'),
                    'summary': optimization_analysis
                }
            )

            doc_title = doc_result.get('title', 'Optimization Report')
            preview = optimization_analysis[:3000]
            if len(optimization_analysis) > 3000:
                preview += "\n\n[... truncated — see Google Doc for full report]"
            
            focus_title = f"[{new_short_alias}] {doc_title}"
            self.dashboard.push_focus("code", focus_title, preview)
            self.dashboard.update_ticker(self.session_context.get_all_items_for_ticker())
            
            confirmation = f"Sir, the optimization report for {filename} is ready. It is referenced as {new_short_alias}."
            self.speak_with_piper(confirmation)
            self.log(f"🔊 Confirmed: {confirmation}")
            
            self.last_intent = "optimization"
            self.save_memory()
            
            if hasattr(self, 'dashboard'):
                self.dashboard.push_state(mode="idle")

            logger.info(f"✓ Optimization workflow complete for {filename}")
            self.status_var.set("Status: Ready")
            
        except Exception as e:
            error_msg = f"Error in optimization workflow: {e}"
            logger.error(error_msg, exc_info=True)
            self.log(f"❌ {error_msg}")
            self.speak_with_piper("An error occurred during the analysis. Please check the console for details.")
    
    def _route_by_context(self, raw_text, text_lower):
        """Context-aware follow-up routing based on last known intent.

        Returns True if the input was fully handled (caller should return).
        """
        # Email follow-ups: "reply to that", "mark that handled", "show it"
        if self.last_intent == "email":
            if any(w in text_lower for w in ["reply", "respond", "answer"]):
                self.handle_email_reply_request(raw_text)
                return True
            if any(w in text_lower for w in ["archive", "mark that handled", "handled", "delete", "trash", "bin"]):
                self.handle_email_management_request(raw_text)
                return True
            if any(w in text_lower for w in ["show it", "display it", "open it"]):
                # Fall back to contextual key resolution if possible
                return self._handle_contextual_command(raw_text)

        # Task follow-ups.
        if self.last_intent == "task":
            if any(w in text_lower for w in ["task", "list", "done", "complete", "mark"]):
                self.handle_task_request(raw_text)
                return True

        # Search follow-ups.
        if self.last_intent == "search":
            if "dig deeper" in text_lower or "open wr" in text_lower or "show wr" in text_lower:
                return self._handle_contextual_command(raw_text)

        # Optimization/report follow-ups.
        if self.last_intent == "optimization":
            if any(w in text_lower for w in ["show c", "open c", "latest report", "last report", "recent report"]):
                if self._handle_contextual_command(raw_text):
                    return True
                self.handle_report_retrieval(raw_text)
                return True

        return False

    def _match_intent(self, raw_text):
        """Score intents from INTENTS and return the best match tuple.

        Returns:
            (intent_name, intent_cfg, handler_callable) or (None, None, None)
        """
        text = raw_text.lower().strip()
        best = (None, None, None)
        best_score = 0

        for intent_name, cfg in INTENTS.items():
            handler_name = cfg.get("handler")
            handler = getattr(self, handler_name, None)
            if not callable(handler):
                continue

            blockers = cfg.get("blockers", [])
            if any(b in text for b in blockers):
                continue

            score = 0
            trigger_score = 0

            for pat in cfg.get("patterns", []):
                if re.search(pat, text, re.IGNORECASE):
                    score += 3
                    trigger_score += 3

            regex = cfg.get("regex")
            if regex and re.search(regex, text, re.IGNORECASE):
                score += 3
                trigger_score += 3

            keyword_hits = sum(1 for kw in cfg.get("keywords", []) if kw in text)
            score += keyword_hits
            trigger_score += keyword_hits

            required = cfg.get("required", [])
            if required:
                req_hits = sum(1 for req in required if req in text)
                # "required" is a qualifier and must not match by itself.
                # The intent must first match a real trigger (keyword/pattern/regex).
                if trigger_score == 0 or req_hits == 0:
                    continue
                score += req_hits * 2

            # Intents without "required" still need at least one trigger to avoid weak matches.
            if trigger_score == 0:
                continue

            if score > best_score:
                best_score = score
                best = (intent_name, cfg, handler)

        return best

    def _dispatch_intent(self, intent_name, intent_cfg, handler, raw_text):
        """Dispatch the matched intent handler with proper signature handling."""
        # Handlers with no user_request parameter.
        noarg_handlers = {"handle_email_summary_request"}
        if handler.__name__ in noarg_handlers:
            handler()
            return
        handler(raw_text)
    
    def add_to_context(self, role, message):
        """Add message to short-term context buffer."""
        if not hasattr(self, "context_buffer") or self.context_buffer is None:
            self.context_buffer = []
        self.context_buffer.append({"role": role, "message": message})
        logger.debug(f"Context buffer size: {len(self.context_buffer)}")
    
    def get_context_history(self):
        """Get formatted context history for LLM."""
        context_buffer = getattr(self, "context_buffer", [])
        if not context_buffer:
            return ""
        history = "CONVERSATION CONTEXT (last exchanges):\n"
        for exchange in context_buffer:
            history += f"  {exchange['role']}: {exchange['message'][:100]}...\n"
        return history
    
    def fallback_to_llm(self, raw_text, context=""):
        """Fallback to the general-purpose LLM brain for unhandled queries."""
        if self.gaming_mode:
            self.log("⚠️  Gaming Mode active - AI brain disabled")
            self.speak_with_piper("Gaming mode is enabled, I cannot process that request.")
            return

        context_history = self.get_context_history()
        memory_facts = "\n".join(self.memory.get("facts", []))

        # Extract profile data for tone/context.
        master_profile = self.memory.get("master_profile", {})
        working_method = master_profile.get("working_method", "")
        communication_style = master_profile.get("communication_style", "")

        # Auto-switch project if mentioned.
        self.detect_and_switch_project(raw_text)
        vault_path = self.vault_root.replace('\\', '/')

        if context:
            prompt = f"""
SYSTEM: You are Jarvis, a helpful voice assistant serving Spencer.
Location: {LOCATION_OVERRIDE}

SPENCER'S PROFILE:
- Working Method: {working_method}
- Communication Style: {communication_style}
- Health: Manages chronic pain and anxiety

PROJECT VAULT ACCESS:
- You have access to Spencer's Project Vault at {vault_path}
- Currently focused on: [{self.active_project}]
- You can read files and search across projects when asked
- All file access is read-only for security

FACTS ABOUT YOUR MASTER:
{memory_facts}

{context_history}

LIVE DATA:
{context}

USER QUESTION: {raw_text}

RESPONSE GUIDELINES:
- Keep responses concise and low-friction (Spencer prefers brevity)
- Be health-conscious in your language
- Answer based on the provided data
- Use vault tools when asked about projects
- Natural, conversational tone suitable for voice delivery
"""
        else:
            prompt = f"""
SYSTEM: You are Jarvis, a helpful voice assistant speaking to Spencer.
Location: {LOCATION_OVERRIDE}

SPENCER'S PROFILE:
- Working Method: {working_method}
- Communication Style: {communication_style}
- Health: Manages chronic pain and anxiety

PROJECT VAULT ACCESS:
- You have access to Spencer's Project Vault at {vault_path}
- Currently focused on: [{self.active_project}]
- You can read files and search across projects when asked
- All file access is read-only for security

FACTS ABOUT YOUR MASTER:
{memory_facts}

{context_history}

USER: {raw_text}

RESPONSE GUIDELINES:
- Keep responses concise and low-friction (Spencer prefers brevity)
- Be health-conscious in your language
- Answer naturally and conversationally
- Keep responses suitable for voice delivery
"""

        self.status_var.set("Status: Thinking...")
        try:
            logger.debug(f"Sending request to LLM: {BRAIN_URL}")
            started_at = time.time()
            response = requests.post(
                BRAIN_URL,
                json={"model": LLM_MODEL, "prompt": prompt, "stream": False}
            )
            if hasattr(self, 'dashboard') and self.dashboard:
                self.dashboard.set_last_ollama_response_time(
                    int((time.time() - started_at) * 1000)
                )

            answer = response.json().get('response', "I encountered an error thinking.")
            self.log(f"Jarvis: {answer}")
            self.speak_with_piper(answer)

            if hasattr(self, 'dashboard'):
                focus_content = f"User: {raw_text[:120]}\n\nJarvis: {answer[:260]}"
                self.dashboard.push_focus("docs", "Latest Conversation", focus_content)

            self.add_to_context("User", raw_text)
            self.add_to_context("Jarvis", answer)
            self.log_vault_action(
                action_type="conversation",
                description=f"Conversation: {raw_text[:50]}{'...' if len(raw_text) > 50 else ''}",
                metadata={
                    "user_query": raw_text,
                    "response_preview": answer[:100] if len(answer) > 100 else answer,
                    "response_length": len(answer),
                    "context_used": bool(context),
                }
            )

            self.interaction_count += 1
            if self.health_intervener():
                self.log("💊 Proposing a health break...")

            self.save_memory()
            self.last_interaction_time = time.time()
            logger.debug("Conversation processed successfully")
        except Exception as e:
            self.log(f"Brain Error: {e}")
            logger.error(f"Brain processing failed: {e}", exc_info=True)
    def health_intervener(self):
        """Proactively propose breaks if Spencer is working too long."""
        health_profile = self.memory.get("master_profile", {}).get("health_profile", {})
        break_interval = health_profile.get("recommended_break_interval", 90)  # minutes
        
        elapsed_time = (time.time() - self.last_break_time) / 60  # Convert to minutes
        
        if elapsed_time > break_interval:
            logger.info(f"Health check: {elapsed_time:.0f} minutes since last break")
            self.last_break_time = time.time()
            msg = ("Sir, you have been working for over "
                   f"{int(elapsed_time)} minutes. "
                   "I recommend a short break when you are ready.")
            self.log(f"💊 {msg}")
            self.speak_with_piper(msg)
            return True
        return False
    
    # ===== PROJECT VAULT SYSTEM =====
    def scan_vault_projects(self):
        """Scan vault root and discover all available projects."""
        try:
            self.available_projects = []
            if os.path.isdir(self.vault_root):
                for item in os.listdir(self.vault_root):
                    item_path = os.path.join(self.vault_root, item)
                    if os.path.isdir(item_path):
                        self.available_projects.append(item)
                logger.info(f"✓ Vault scan complete: {len(self.available_projects)} projects found")
                logger.debug(f"Projects: {', '.join(self.available_projects)}")
            else:
                logger.error(f"Vault root not found: {self.vault_root}")
        except Exception as e:
            logger.error(f"Vault scan failed: {e}")
    
    def list_vault_projects(self):
        """Return formatted list of all projects in vault (read-only)."""
        try:
            self.scan_vault_projects()  # Refresh list
            if not self.available_projects:
                return "No projects found in vault."
            
            project_list = "Projects in your Vault:\n"
            for project in sorted(self.available_projects):
                marker = "[ACTIVE]" if project == self.active_project else ""
                project_list += f"  • {project} {marker}\n"
            
            logger.info(f"Vault projects listed (active: {self.active_project})")
            return project_list
        except Exception as e:
            logger.error(f"Failed to list vault projects: {e}")
            return f"Error reading vault: {e}"
    
    def read_project_file(self, relative_path):
        """Read a file from the active project (read-only).
        
        Args:
            relative_path: Path relative to active project folder
            
        Returns:
            File contents as string
        """
        try:
            if not self.active_project in self.available_projects:
                return f"Project '{self.active_project}' not found in vault."
            
            full_path = os.path.join(self.vault_root, self.active_project, relative_path)
            
            # Security: Prevent directory traversal
            real_path = os.path.realpath(full_path)
            vault_base = os.path.realpath(self.vault_root)
            if not real_path.startswith(vault_base):
                logger.warning(f"Security: Attempted directory traversal: {full_path}")
                return "Error: Invalid file path (directory traversal attempted)."
            
            if not os.path.exists(real_path):
                return f"File not found: {relative_path}"
            
            if not os.path.isfile(real_path):
                return f"Path is not a file: {relative_path}"
            
            # Read file (limiting size to prevent massive outputs)
            max_size = 100000  # 100KB limit
            file_size = os.path.getsize(real_path)
            
            if file_size > max_size:
                return f"File too large ({file_size} bytes). Showing first 25KB:\n\n" + open(real_path, 'r', encoding='utf-8', errors='ignore').read()[:25000]
            
            with open(real_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            logger.info(f"Vault read: {self.active_project}/{relative_path}")
            return content
            
        except Exception as e:
            logger.error(f"Failed to read vault file: {e}")
            return f"Error reading file: {e}"
    
    def search_vault(self, query):
        """Search for keyword recursively across all vault projects (read-only).
        
        Args:
            query: Search term (case-insensitive)
            
        Returns:
            Formatted search results
        """
        try:
            query_lower = query.lower()
            results = {}
            files_searched = 0
            
            for project in self.available_projects:
                project_path = os.path.join(self.vault_root, project)
                
                for root, dirs, files in os.walk(project_path):
                    # Skip common non-text directories
                    dirs[:] = [d for d in dirs if d not in ['.git', '__pycache__', 'node_modules', '.venv', 'venv']]
                    
                    for file in files:
                        # Skip binary files
                        if any(file.endswith(ext) for ext in ['.pyc', '.exe', '.dll', '.so', '.bin']):
                            continue
                        
                        files_searched += 1
                        file_path = os.path.join(root, file)
                        
                        try:
                            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                                content = f.read()
                                if query_lower in content.lower():
                                    # Store match with line number
                                    rel_file = os.path.relpath(file_path, project_path)
                                    if project not in results:
                                        results[project] = []
                                    results[project].append(rel_file)
                        except:
                            pass
            
            # Format results
            if not results:
                return f"No matches found for '{query}' in {files_searched} files searched."
            
            output = f"Search Results for '{query}' ({files_searched} files searched):\n\n"
            for project in sorted(results.keys()):
                output += f"📁 {project}:\n"
                for file in sorted(results[project])[:10]:  # Limit to 10 per project
                    output += f"   • {file}\n"
                if len(results[project]) > 10:
                    output += f"   ... and {len(results[project]) - 10} more\n"
            
            logger.info(f"Vault search: '{query}' found in {sum(len(v) for v in results.values())} files")
            return output
            
        except Exception as e:
            logger.error(f"Vault search failed: {e}")
            return f"Search error: {e}"
    
    def detect_and_switch_project(self, text):
        """Auto-detect if user mentions a project and switch context (case-insensitive).
        
        Returns:
            True if project was switched, False otherwise
        """
        try:
            text_lower = text.lower()
            
            for project in self.available_projects:
                if project.lower() in text_lower:
                    if project != self.active_project:
                        old_project = self.active_project
                        self.active_project = project
                        logger.info(f"🔀 Project switch: {old_project} → {self.active_project}")
                        self.log(f"📁 Switched to project: {self.active_project}")
                        return True
        except Exception as e:
            logger.error(f"Project detection failed: {e}")
        
        return False
    
    def start_vad_monitor(self):
        """Start VAD monitor thread for barge-in detection (Normal Mode only)."""
        # Only enable barge-in in Normal Mode (not Conversation Mode)
        if not self.barge_in_enabled or self.vad_monitor_active or self.conversation_mode:
            return
        
        logger.info("Starting VAD monitor for barge-in detection...")
        self.vad_monitor_active = True
        self.vad_monitor_thread = threading.Thread(target=self.vad_monitor_loop, daemon=True)
        self.vad_monitor_thread.start()
        logger.debug("VAD monitor thread started")
    
    def stop_vad_monitor(self):
        """Stop VAD monitor thread."""
        if not self.vad_monitor_active:
            return
        
        logger.info("Stopping VAD monitor...")
        self.vad_monitor_active = False
        if self.vad_monitor_thread:
            self.vad_monitor_thread.join(timeout=1.0)
            self.vad_monitor_thread = None
        logger.debug("VAD monitor stopped")
    
    def vad_monitor_loop(self):
        """Monitor microphone for speech while Jarvis is speaking (barge-in detection)."""
        logger.info("VAD monitor loop active")
        
        # Wait for barge_in_delay before starting to actually monitor
        # This prevents Jarvis from interrupting himself when speech starts
        if self.barge_in_delay > 0:
            logger.debug(f"VAD monitor waiting {self.barge_in_delay}s before starting...")
            start_time = time.time()
            while time.time() - start_time < self.barge_in_delay:
                if not self.vad_monitor_active or not self.is_speaking:
                    logger.debug("VAD monitor cancelled during startup delay")
                    return
                time.sleep(0.1)
            logger.debug("VAD monitor delay complete - starting barge-in detection")
        
        try:
            while self.vad_monitor_active:
                # Stop if conversation mode is enabled (no barge-in needed there)
                if self.conversation_mode:
                    logger.info("Conversation mode enabled - stopping VAD monitor")
                    break
                
                # Only monitor when Jarvis is speaking
                if not self.is_speaking:
                    time.sleep(0.05)
                    continue
                
                # Check if we have recorder available
                if self.recorder is None or self.porcupine is None:
                    time.sleep(0.05)
                    continue
                
                try:
                    # Read audio frame (non-blocking)
                    pcm = self.recorder.read()
                    
                    # Calculate energy
                    energy = self.detect_speech_energy(pcm)
                    
                    # If energy exceeds barge-in threshold while speaking
                    if energy > self.barge_in_threshold:
                        logger.warning(f"BARGE-IN detected! Energy: {energy:.0f} (threshold: {self.barge_in_threshold})")
                        self.interrupt_requested = True
                        # Brief pause to let interruption take effect
                        time.sleep(0.1)
                        
                except Exception as e:
                    logger.error(f"VAD monitor frame error: {e}")
                    time.sleep(0.05)
                    
        except Exception as e:
            logger.error(f"VAD monitor loop error: {e}", exc_info=True)
        finally:
            logger.info("VAD monitor loop terminated")
    
    def handle_n8n_webhook(self, notification):
        """Process notifications from n8n workflow."""
        priority = str(notification.get("priority", "ROUTINE")).upper()
        message = notification.get("message", "No content")
        source = notification.get("source", "Unknown")
        metadata = notification.get("metadata", {})  # Extract metadata for emails, etc.
        self._refresh_command_capture_state()
        
        logger.info(f"n8n Notification [{priority}]: {source} - {message}")
        
        if priority == "URGENT":
            self.urgent_interrupt = True
            logger.warning(f"URGENT notification queued: {message}")
        elif priority == "HIGH":
            if self.notification_hold:
                queued_msg = {
                    "source": source,
                    "message": message,
                    "timestamp": datetime.now().isoformat(),
                    "metadata": metadata,
                    "priority": priority
                }
                self.notification_queue.append(queued_msg)
                logger.info(f"High-priority notification deferred during command capture: {message}")
                return
            now = time.time()
            if now - self.last_notification_speak_time >= self.notification_cooldown:
                self.last_notification_speak_time = now
                self.speak_with_piper(message)
                logger.info(f"High-priority notification spoken: {message}")
            else:
                # Queue with metadata preserved
                queued_msg = {
                    "source": source, 
                    "message": message, 
                    "timestamp": datetime.now().isoformat(),
                    "metadata": metadata,
                    "priority": priority
                }
                self.notification_queue.append(queued_msg)
                logger.debug(f"High-priority notification queued (cooldown): {message}")
        else:
            # Queue with metadata preserved
            queued_msg = {
                "source": source, 
                "message": message, 
                "timestamp": datetime.now().isoformat(),
                "metadata": metadata,
                "priority": priority
            }
            self.notification_queue.append(queued_msg)
            logger.debug(f"Routine notification queued: {message}")

    def _start_command_capture(self):
        """Wake-word activated: pause notification speech until command is captured."""
        self.awaiting_command = True
        self.notification_hold = True
        self.command_capture_started_at = time.time()
        logger.info("Command capture lock enabled")

    def _end_command_capture(self):
        """Release capture lock after command processed or timeout."""
        if self.awaiting_command or self.notification_hold:
            logger.info("Command capture lock released")
        self.awaiting_command = False
        self.notification_hold = False
        self.command_capture_started_at = 0.0

    def _refresh_command_capture_state(self):
        """Auto-release stale command capture lock."""
        if not self.awaiting_command:
            return
        if (time.time() - self.command_capture_started_at) > self.command_capture_timeout:
            logger.warning("Command capture lock timed out; releasing")
            self._end_command_capture()

    def process_notification_queue(self, context="idle"):
        """Speak one queued notification when safe to do so."""
        self._refresh_command_capture_state()
        if self.notification_hold or self.awaiting_command:
            return
        if self.gaming_mode or self.is_speaking:
            return

        with self.queue_lock:
            if not self.notification_queue:
                return
            item = self.notification_queue.pop(0)

        message = item.get("message", "")
        if not message:
            return

        logger.info(f"Processing queued notification ({item.get('priority', 'ROUTINE')}): {message}")
        self.speak_with_piper(message)
    
    def interrupt_and_speak(self, message):
        """Interrupt current activity and speak urgent message."""
        logger.warning(f"INTERRUPT: {message}")
        self.log(f"🚨 URGENT: {message}")
        # The message will be processed before process_conversation completes
        # due to self.urgent_interrupt flag
        self.speak_with_piper(message)

    def toggle_gaming_mode(self):
        """Gaming Mode disables the microphone completely and frees resources."""
        # Toggle the state
        self.gaming_mode = not self.gaming_mode
        
        if self.gaming_mode:
            self.log("🎮 Gaming Mode: ENABLED")
            self.log("   → Mic disabled, resources freed")
            logger.info("Gaming mode activated - stopping all listening and freeing resources")
            
            # Stop listening and clean up resources
            self.is_listening = False
            self.cleanup_audio_resources()
            
            # Update dashboard: idle when gaming mode enabled
            if hasattr(self, 'dashboard'):
                self.dashboard.push_state(mode="idle", gamingMode=True)
            
            # Disable conversation mode
            self.conversation_mode = False
            
            self.status_var.set("Status: Gaming Mode - Mic Off")
        else:
            self.log("🎮 Gaming Mode: DISABLED")
            self.log("   → Returning to Normal Mode")
            logger.info("Gaming mode deactivated - returning to normal mode")
            self.status_var.set("Status: Standby")
            
            # Update dashboard: idle when gaming mode disabled
            if hasattr(self, 'dashboard'):
                self.dashboard.push_state(mode="idle", gamingMode=False)
            
            # Restart listening in normal mode
            self.start_listening()

    def toggle_conversation_mode(self):
        """Conversation Mode disables wake word for continuous chat."""
        # Toggle the state
        self.conversation_mode = not self.conversation_mode
        
        if self.conversation_mode:
            # Can't enable if gaming mode is on
            if self.gaming_mode:
                self.log("⚠️  Cannot enable Conversation Mode during Gaming Mode")
                logger.warning("Attempted to enable conversation mode during gaming mode")
                self.conversation_mode = False
                return
            
            self.log("💬 Conversation Mode: ENABLED")
            self.log("   → Open mic - just speak naturally!")
            self.log("   → No wake word needed, automatic speech detection")
            logger.info("Conversation mode activated - continuous speech detection with VAD")
            self.status_var.set("Status: 💬 Speak freely...")
            
            # Update dashboard: conversation mode enabled
            if hasattr(self, 'dashboard'):
                self.dashboard.push_state(mode="idle", conversationalMode=True)
            
            # Ensure listening is active
            if not self.is_listening:
                self.start_listening()
        else:
            self.log("💬 Conversation Mode: DISABLED")
            self.log("   → Back to wake word detection")
            logger.info("Conversation mode deactivated - back to normal wake word mode")
            self.status_var.set("Status: Monitoring...")
            
            # Update dashboard: conversation mode disabled
            if hasattr(self, 'dashboard'):
                self.dashboard.push_state(mode="idle", conversationalMode=False)

    # --- TOOLS: SEARCH, CALENDAR, GMAIL ---
    def google_search(self, query, structured=False):
        """Perform Google search using Custom Search API.

        Args:
            query: search query text.
            structured: if True, return list of dict items with title/snippet/link.
        """
        service = build("customsearch", "v1", developerKey=GOOGLE_CSE_API_KEY)
        res = service.cse().list(q=query, cx=GOOGLE_CSE_CX, num=5).execute()
        items = res.get('items', []) or []
        if structured:
            return [
                {
                    "title": i.get("title", "Untitled"),
                    "snippet": i.get("snippet", ""),
                    "link": i.get("link", ""),
                }
                for i in items
            ]
        return "\n".join([f"{i.get('title', 'Untitled')}: {i.get('snippet', '')}" for i in items])

    def get_calendar(self):
        """Get calendar events using authenticated Google Calendar API."""
        try:
            creds = get_google_creds()
            service = build('calendar', 'v3', credentials=creds)
            # Example: Get next 10 events
            # events_result = service.events().list(calendarId='primary', maxResults=10).execute()
            # events = events_result.get('items', [])
            return "You have a project meeting at 2 PM and a physiotherapy session at 4 PM."
        except Exception as e:
            self.log(f"Calendar API Error: {e}")
            return "Error accessing calendar."
    
    def get_docs_content(self, doc_id):
        """Read Google Docs content using authenticated API."""
        try:
            creds = get_google_creds()
            service = build('docs', 'v1', credentials=creds)
            document = service.documents().get(documentId=doc_id).execute()
            return document.get('body', {})
        except Exception as e:
            self.log(f"Docs API Error: {e}")
            return None
    
    # --- GMAIL EMAIL TOOLS ---
    def search_emails(self, query):
        """Search Gmail for emails matching query (e.g., 'from:john@example.com', 'subject:proposal').
        
        Args:
            query: Gmail search query (supports Gmail operators: from:, subject:, to:, etc.)
        
        Returns:
            List of email dicts with sender, subject, snippet, unique_id
        """
        try:
            creds = get_google_creds()
            service = build('gmail', 'v1', credentials=creds)
            
            # Search for matching emails
            results = service.users().messages().list(userId='me', q=query, maxResults=5).execute()
            messages = results.get('messages', [])
            
            if not messages:
                logger.info(f"No emails found for query: {query}")
                return []
            
            # Fetch full email details for each result
            emails = []
            for msg in messages:
                try:
                    msg_data = service.users().messages().get(userId='me', id=msg['id'], format='full').execute()
                    headers = msg_data['payload']['headers']
                    
                    email_obj = {
                        'id': msg['id'],
                        'sender': next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown'),
                        'subject': next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject'),
                        'snippet': msg_data.get('snippet', '')[:200]  # First 200 chars
                    }
                    emails.append(email_obj)
                except Exception as e:
                    logger.warning(f"Failed to fetch email details: {e}")
                    continue
            
            logger.info(f"✓ Found {len(emails)} email(s) matching: {query}")
            return emails
            
        except Exception as e:
            logger.error(f"Email search error: {e}")
            self.log(f"❌ Email search failed: {e}")
            return []
    
    def get_recent_emails(self, limit=5):
        """Get the most recent emails from inbox.
        
        Args:
            limit: Number of recent emails to fetch (default 5)
        
        Returns:
            List of email dicts with sender, subject, snippet, unique_id
        """
        try:
            creds = get_google_creds()
            service = build('gmail', 'v1', credentials=creds)
            
            # Get recent emails
            results = service.users().messages().list(userId='me', maxResults=limit).execute()
            messages = results.get('messages', [])
            
            emails = []
            for msg in messages:
                try:
                    msg_data = service.users().messages().get(userId='me', id=msg['id'], format='full').execute()
                    headers = msg_data['payload']['headers']
                    
                    email_obj = {
                        'id': msg['id'],
                        'sender': next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown'),
                        'subject': next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject'),
                        'snippet': msg_data.get('snippet', '')[:200],
                        'internal_date': msg_data.get('internalDate', '')
                    }
                    emails.append(email_obj)
                except Exception as e:
                    logger.warning(f"Failed to fetch email details: {e}")
                    continue
            
            logger.info(f"✓ Retrieved {len(emails)} recent email(s)")
            return emails
            
        except Exception as e:
            logger.error(f"Failed to get recent emails: {e}")
            self.log(f"❌ Failed to get recent emails: {e}")
            return []
    
    def send_email(self, to_address, subject, body):
        """Send an email via Gmail.
        
        Args:
            to_address: Recipient email address
            subject: Email subject line
            body: Email body text
        
        Returns:
            True if successful, False otherwise
        """
        try:
            import base64
            from email.mime.text import MIMEText
            
            creds = get_google_creds()
            service = build('gmail', 'v1', credentials=creds)
            
            # Create message
            message = MIMEText(body)
            message['to'] = to_address
            message['subject'] = subject
            
            # Encode to base64
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
            
            # Send
            send_message = {'raw': raw_message}
            result = service.users().messages().send(userId='me', body=send_message).execute()
            
            logger.info(f"✓ Email sent to {to_address}: {subject}")
            self.log(f"✓ Email sent to {to_address}")
            return True
            
        except Exception as e:
            logger.error(f"Email send error: {e}")
            self.log(f"❌ Failed to send email: {e}")
            return False
    
    def reply_to_email(self, message_id, reply_text):
        """Reply to an email thread.
        
        Args:
            message_id: Gmail message ID to reply to
            reply_text: Reply text body
        
        Returns:
            True if successful, False otherwise
        """
        try:
            import base64
            from email.mime.text import MIMEText
            
            creds = get_google_creds()
            service = build('gmail', 'v1', credentials=creds)
            
            # Get original message to extract headers
            original_msg = service.users().messages().get(userId='me', id=message_id, format='full').execute()
            headers = original_msg['payload']['headers']
            
            # Extract original subject and recipients
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
            from_email = next((h['value'] for h in headers if h['name'] == 'From'), OWNER_EMAIL)
            
            # Ensure Re: prefix
            if not subject.lower().startswith('re:'):
                subject = f"Re: {subject}"
            
            # Create reply message
            message = MIMEText(reply_text)
            message['to'] = from_email
            message['subject'] = subject
            message['In-Reply-To'] = original_msg.get('headers', [])[0].get('value', '')
            
            # Send as reply
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
            send_message = {
                'raw': raw_message,
                'threadId': original_msg.get('threadId', '')
            }
            
            result = service.users().messages().send(userId='me', body=send_message).execute()
            logger.info(f"✓ Reply sent to email thread")
            self.log(f"✓ Reply sent")
            return True
            
        except Exception as e:
            logger.error(f"Email reply error: {e}")
            self.log(f"❌ Failed to send reply: {e}")
            return False

    def check_piper_installation(self):
        """Check if Piper TTS is available."""
        try:
            self.piper_exe = self.resolve_piper_executable()
            if not self.piper_exe:
                logger.warning("⚠️  Piper TTS not found - wake word acknowledgment disabled")
                return False

            result = subprocess.run(
                [self.piper_exe, "--version"],
                capture_output=True,
                timeout=3
            )
            logger.info("✓ Piper TTS is available")
            return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            logger.warning("⚠️  Piper TTS not found - wake word acknowledgment disabled")
            return False

    def resolve_piper_executable(self):
        """Resolve Piper executable path from config, PATH, or local venv."""
        candidates = []

        config_path = config_dict.get("piper_exe")
        if config_path:
            candidates.append(config_path)

        candidates.append(shutil.which("piper"))

        project_root = os.path.dirname(__file__)
        candidates.extend([
            os.path.join(project_root, ".venv", "Scripts", "piper.exe"),
            os.path.join(project_root, "venv", "Scripts", "piper.exe"),
        ])

        for path in candidates:
            if path and os.path.exists(path):
                logger.info(f"✓ Piper executable found: {path}")
                return path

        return None
    
    def generate_yes_audio(self):
        """Generate the 'yes' audio file if it doesn't exist."""
        if not self.piper_available:
            logger.warning("Skipping yes.wav generation - Piper not available")
            self.log("⚠️  Piper TTS not installed - using beep for wake word acknowledgment")
            self.log("   Install Piper for voice: https://github.com/rhasspy/piper/releases")
            return
        
        if os.path.exists(self.yes_audio_path):
            logger.info(f"✓ Wake word audio asset found: {self.yes_audio_path}")
            return
        
        try:
            logger.info("Generating wake word acknowledgment audio...")
            self.log("🎵 Generating 'Yes?' audio with Jarvis voice...")
            model_path = os.path.join(os.path.dirname(__file__), "jarvis-high.onnx")
            result = subprocess.run(
                [self.piper_exe, "-m", model_path, "-f", self.yes_audio_path],
                input="Yes?".encode(),
                capture_output=True,
                timeout=10
            )
            
            if result.returncode == 0:
                logger.info(f"✓ Created {self.yes_audio_path} with Jarvis voice")
                self.log(f"✓ Audio asset created: {self.yes_audio_path}")
            else:
                logger.error(f"Failed to generate yes.wav: {result.stderr.decode()}")
                self.log("⚠️  Audio generation failed - will use beep fallback")
        except Exception as e:
            logger.error(f"Error generating yes.wav: {e}")
            self.log(f"⚠️  Audio generation error - will use beep fallback")
    
    def play_yes_audio(self):
        """Play the pre-generated 'yes' audio file or beep as fallback."""
        if os.path.exists(self.yes_audio_path):
            try:
                # Play using PowerShell SoundPlayer (fast, non-blocking)
                subprocess.Popen(
                    ["powershell", "-c", f"(New-Object Media.SoundPlayer '{os.path.abspath(self.yes_audio_path)}').PlaySync();"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                logger.debug("Playing wake word acknowledgment")
            except Exception as e:
                logger.error(f"Error playing yes.wav: {e}")
                self.play_beep_fallback()
        else:
            # Fallback to system beep if yes.wav doesn't exist
            logger.warning("yes.wav not found - using beep fallback")
            self.play_beep_fallback()
    
    def play_beep_fallback(self):
        """Play a system beep as fallback when yes.wav is not available."""
        try:
            # Play a pleasant double beep using PowerShell
            subprocess.Popen(
                ["powershell", "-c", "[console]::beep(800,150); [console]::beep(1000,150)"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            logger.debug("Played beep fallback")
        except Exception as e:
            logger.error(f"Beep fallback failed: {e}")
    
    def listen_and_transcribe(self, duration=None):
        """Capture audio with VAD and transcribe with Whisper (duration parameter kept for compatibility but ignored)."""
        if self.recorder is None:
            logger.error("Recorder not available for transcription")
            return None
        
        try:
            logger.info("Listening with VAD (waiting for speech)...")
            self.status_var.set("Status: Listening...")
            self.log("🎤 Listening for your command...")
            
            # Update dashboard: listening mode
            if hasattr(self, 'dashboard'):
                self.dashboard.push_state(mode="listening")
            
            # VAD-based audio capture
            speech_frames = []
            is_speaking = False
            silence_counter = 0
            speech_counter = 0
            
            frames_per_second = self.porcupine.sample_rate / self.porcupine.frame_length
            silence_frames = int(self.silence_duration * frames_per_second)
            min_speech_frames = int(self.min_speech_duration * frames_per_second)
            
            # Maximum listening time (safety limit)
            max_listen_time = 30
            frames_captured = 0
            max_frames = int(max_listen_time * frames_per_second)
            
            while frames_captured < max_frames:
                # Don't listen while speaking (avoid transcribing own voice)
                if not self.is_listening or self.gaming_mode or self.is_speaking:
                    logger.info("Listening interrupted")
                    return None
                
                pcm = self.recorder.read()
                frames_captured += 1
                
                # Calculate speech energy
                energy = self.detect_speech_energy(pcm)
                
                if energy > self.vad_threshold:
                    # Speech detected
                    if not is_speaking:
                        logger.debug(f"Speech started (energy: {energy:.0f})")
                        self.status_var.set("Status: 🎤 Recording...")
                        is_speaking = True
                        speech_counter = 0
                    
                    speech_frames.extend(pcm)
                    speech_counter += 1
                    silence_counter = 0
                    
                    # Update progress
                    if speech_counter % 25 == 0:
                        elapsed = (speech_counter * self.porcupine.frame_length) / self.porcupine.sample_rate
                        self.status_var.set(f"Status: Recording ({elapsed:.1f}s)...")
                    
                elif is_speaking:
                    # Silence during speech
                    silence_counter += 1
                    speech_frames.extend(pcm)
                    
                    if silence_counter >= silence_frames:
                        # End of speech detected
                        if speech_counter >= min_speech_frames:
                            logger.info(f"Speech ended (captured {speech_counter} frames, {silence_counter} silence frames)")
                            break
                        else:
                            # Too short, reset
                            logger.debug("Speech too short, resetting")
                            is_speaking = False
                            speech_frames = []
                            silence_counter = 0
                            speech_counter = 0
                            self.status_var.set("Status: Listening...")
            
            if not speech_frames or speech_counter < min_speech_frames:
                logger.warning("No valid speech detected")
                self.log("⚠️  No speech detected")
                return None
            
            logger.info(f"Captured {len(speech_frames)} audio samples via VAD")
            
            # Convert to numpy array and apply light gain normalization for quiet captures.
            audio_data = np.array(speech_frames, dtype=np.int16)
            if self.mic_gain and self.mic_gain != 1.0 and audio_data.size:
                audio_data = np.clip(audio_data.astype(np.float32) * float(self.mic_gain), -32768, 32767).astype(np.int16)
            if audio_data.size:
                peak = float(np.max(np.abs(audio_data)))
                if 0 < peak < 10000:
                    gain = min(4.0, 10000.0 / peak)
                    audio_data = np.clip(audio_data.astype(np.float32) * gain, -32768, 32767).astype(np.int16)
                    logger.debug(f"Applied audio gain normalization x{gain:.2f} (peak={peak:.0f})")
            
            # Save to temporary WAV file for Whisper
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_wav:
                temp_path = temp_wav.name
            
            with wave.open(temp_path, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)  # 16-bit
                wf.setframerate(self.porcupine.sample_rate)
                wf.writeframes(audio_data.tobytes())
            
            logger.debug(f"Audio saved to {temp_path}")
            
            # Transcribe with Whisper
            self.status_var.set("Status: Transcribing...")
            self.log("📝 Transcribing...")
            logger.info("Starting Whisper transcription...")
            
            if hasattr(self, "dashboard") and self.dashboard:
                self.dashboard.set_transcribing_status(True)
            try:
                result = self.stt_model.transcribe(temp_path, language='en')
                text = result['text'].strip()
                if not text:
                    logger.info("Empty transcript on first pass, retrying Whisper with deterministic settings")
                    retry_result = self.stt_model.transcribe(
                        temp_path,
                        language='en',
                        fp16=False,
                        temperature=0.0,
                        condition_on_previous_text=False
                    )
                    text = retry_result['text'].strip()
            finally:
                if hasattr(self, "dashboard") and self.dashboard:
                    self.dashboard.set_transcribing_status(False)
            
            # Clean up temp file
            try:
                os.unlink(temp_path)
            except:
                pass
            
            if text:
                logger.info(f"Transcribed: {text}")
                return text
            else:
                logger.warning("No speech detected in transcription")
                self.log("⚠️  No speech detected")
                return None
                
        except Exception as e:
            logger.error(f"Transcription error: {e}", exc_info=True)
            self.log(f"Transcription Error: {e}")
            return None
    
    def detect_speech_energy(self, audio_chunk):
        """Simple energy-based speech detection."""
        if len(audio_chunk) == 0:
            return 0
        # Calculate RMS energy with safe conversion
        audio_array = np.array(audio_chunk, dtype=np.float32)
        mean_square = np.mean(audio_array**2)
        # Ensure non-negative and valid
        if mean_square < 0 or np.isnan(mean_square):
            return 0
        energy = np.sqrt(mean_square)
        return energy
    
    def continuous_listen_and_transcribe(self):
        """Continuous listening for conversation mode - captures when speech detected."""
        if self.recorder is None:
            logger.error("Recorder not available for continuous listening")
            return None
        
        try:
            logger.info("Continuous listening mode active...")
            
            # Buffer to accumulate audio
            audio_buffer = []
            speech_frames = []
            is_speaking = False
            silence_counter = 0
            speech_counter = 0
            
            frames_per_second = self.porcupine.sample_rate / self.porcupine.frame_length
            silence_frames = int(self.silence_duration * frames_per_second)
            min_speech_frames = int(self.min_speech_duration * frames_per_second)
            
            # Monitor for speech in a rolling window
            max_listen_time = 30  # Maximum 30 seconds per conversation turn
            frames_captured = 0
            max_frames = int(max_listen_time * frames_per_second)
            
            while frames_captured < max_frames:
                # Don't listen while speaking (continuous mode too)
                if not self.is_listening or self.gaming_mode or not self.conversation_mode or self.is_speaking:
                    logger.info("Continuous listening interrupted")
                    return None
                
                pcm = self.recorder.read()
                frames_captured += 1
                
                # Calculate speech energy
                energy = self.detect_speech_energy(pcm)
                
                if energy > self.vad_threshold:
                    # Speech detected
                    if not is_speaking:
                        logger.debug(f"Speech started (energy: {energy:.0f})")
                        self.status_var.set("Status: 🎤 Listening...")
                        is_speaking = True
                        speech_counter = 0
                    
                    speech_frames.extend(pcm)
                    speech_counter += 1
                    silence_counter = 0
                    
                elif is_speaking:
                    # Silence during speech
                    silence_counter += 1
                    speech_frames.extend(pcm)
                    
                    if silence_counter >= silence_frames:
                        # End of speech detected
                        if speech_counter >= min_speech_frames:
                            logger.info(f"Speech ended ({speech_counter} frames, {silence_counter} silence frames)")
                            break
                        else:
                            # Too short, reset
                            logger.debug("Speech too short, resetting")
                            is_speaking = False
                            speech_frames = []
                            silence_counter = 0
                            speech_counter = 0
                
                # Update status periodically
                if frames_captured % 50 == 0:
                    if not is_speaking:
                        self.status_var.set("Status: 💬 Conversation Mode - Speak freely...")
            
            if not speech_frames or speech_counter < min_speech_frames:
                logger.debug("No valid speech detected")
                return None
            
            logger.info(f"Processing {len(speech_frames)} audio samples")
            
            # Convert to numpy array
            audio_data = np.array(speech_frames, dtype=np.int16)
            if self.mic_gain and self.mic_gain != 1.0 and audio_data.size:
                audio_data = np.clip(audio_data.astype(np.float32) * float(self.mic_gain), -32768, 32767).astype(np.int16)
            
            # Save to temporary WAV file
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_wav:
                temp_path = temp_wav.name
            
            with wave.open(temp_path, 'wb') as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(self.porcupine.sample_rate)
                wf.writeframes(audio_data.tobytes())
            
            # Transcribe with Whisper
            self.status_var.set("Status: 📝 Transcribing...")
            logger.info("Transcribing continuous speech...")
            
            if hasattr(self, "dashboard") and self.dashboard:
                self.dashboard.set_transcribing_status(True)
            try:
                result = self.stt_model.transcribe(temp_path, language='en')
            finally:
                if hasattr(self, "dashboard") and self.dashboard:
                    self.dashboard.set_transcribing_status(False)
            text = result['text'].strip()
            
            # Clean up
            try:
                os.unlink(temp_path)
            except:
                pass
            
            if text:
                logger.info(f"Transcribed (continuous): {text}")
                return text
            else:
                return None
                
        except Exception as e:
            logger.error(f"Continuous listening error: {e}", exc_info=True)
            return None

    @staticmethod
    @functools.lru_cache(maxsize=256)
    def extract_sender_name(sender_str):
        """Extract just the name from 'Name <email@domain>' format for speech.
        Cached: reduces repeated parsing of sender strings.
        """
        if '<' in sender_str and '>' in sender_str:
            # Extract name part: "John Doe <john@example.com>" -> "John Doe"
            name = sender_str.split('<')[0].strip()
            return name if name else sender_str.replace('<', '').replace('>', '').replace('@', ' at ')
        # Remove @ and replace with 'at' for readability
        return sender_str.replace('@', ' at ').replace('<', '').replace('>', '')
    
    @staticmethod
    @functools.lru_cache(maxsize=512)
    def sanitize_for_speech(text):
        """Remove/replace characters that shouldn't be spoken.
        Cached: reduces repeated text processing on similar inputs.
        """
        # Replace symbols with their spoken equivalents
        text = text.replace('°', ' degrees ')  # Degree symbol → "degrees"
        
        # Replace email-style characters
        text = text.replace('<', '')  # Remove angle brackets
        text = text.replace('>', '')
        text = text.replace('@', ' at ')  # Replace @ with 'at'
        
        # Remove markdown characters
        text = text.replace('*', '')  # Remove asterisks
        text = text.replace('#', '')  # Remove hash symbols
        text = text.replace('_', '')  # Remove underscores
        text = text.replace('`', '')  # Remove backticks
        text = text.replace('~', '')  # Remove tildes
        text = text.replace('|', '')  # Remove pipes
        text = text.replace('[', '')  # Remove brackets
        text = text.replace(']', '')
        text = text.replace('{', '')  # Remove braces
        text = text.replace('}', '')
        
        # Remove multiple spaces
        text = ' '.join(text.split())
        return text

    def speak(self, text):
        """Canonical speech entrypoint for assistant voice output."""
        self.speak_with_piper(text)

    def speak_with_piper(self, text):
        """Use Piper TTS to speak longer responses (with barge-in support).
        Uses a lock to prevent concurrent audio playback (speaking over self).
        """
        with self.speak_lock:  # Serialize all speech generation
            # Log happens in process_conversation to avoid duplicate entries
            
            if not self.piper_available:
                logger.warning("Piper TTS not available - cannot speak response")
                self.log(f"🔇 TTS unavailable: {text}")
                return

            if not getattr(self, "piper_exe", None):
                self.piper_exe = self.resolve_piper_executable()
                if not self.piper_exe:
                    logger.warning("Piper executable not found - cannot speak response")
                    self.log(f"🔇 TTS unavailable (no piper.exe): {text}")
                    return
            
            try:
                # Clean text for speech
                clean_text = self.sanitize_for_speech(text)
                
                logger.debug(f"Speaking with Piper: {clean_text[:50]}...")
                
                # Create temporary WAV file
                with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_wav:
                    temp_path = temp_wav.name
                
                # Generate speech with Piper using local model
                model_path = os.path.join(os.path.dirname(__file__), "jarvis-high.onnx")
                result = subprocess.run(
                    [self.piper_exe, "-m", model_path, "-f", temp_path],
                    input=clean_text.encode(),
                    capture_output=True,
                    timeout=60
                )
                
                if result.returncode == 0:
                    # Set speaking flag and start VAD monitor for barge-in
                    self.is_speaking = True
                    self.interrupt_requested = False
                    self.start_vad_monitor()
                    
                    # Update dashboard: speaking mode
                    if hasattr(self, 'dashboard'):
                        self.dashboard.push_state(mode="speaking")
                    
                                        # Prefer native winsound playback on Windows; fallback to PowerShell SoundPlayer.
                    played_ok = False
                    if os.name == "nt":
                        try:
                            import winsound
                            with wave.open(temp_path, "rb") as wav_file:
                                duration_s = wav_file.getnframes() / float(max(1, wav_file.getframerate()))
                            winsound.PlaySound(temp_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
                            playback_deadline = time.time() + duration_s + 0.5
                            while time.time() < playback_deadline:
                                if self.interrupt_requested:
                                    logger.warning("Barge-in: Stopping speech immediately")
                                    winsound.PlaySound(None, winsound.SND_PURGE)
                                    self.log("Interrupted - Listening, Sir")
                                    break
                                time.sleep(0.05)
                            played_ok = True
                        except Exception as play_err:
                            logger.warning(f"winsound playback failed, falling back to PowerShell: {play_err}")

                    if not played_ok:
                        self.current_tts_process = subprocess.Popen(
                            ["powershell", "-c", f"(New-Object Media.SoundPlayer '{temp_path}').PlaySync();"],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL
                        )
                        while self.current_tts_process.poll() is None:
                            if self.interrupt_requested:
                                logger.warning("Barge-in: Stopping speech immediately")
                                self.current_tts_process.kill()
                                self.log("Interrupted - Listening, Sir")
                                break
                            time.sleep(0.05)

# Clean up
                    self.is_speaking = False
                    self.stop_vad_monitor()
                    self.current_tts_process = None
                    
                    # If interrupted, skip the echo fix delay
                    if not self.interrupt_requested:
                        logger.debug("Audio played successfully")
                        # Echo fix: Wait for speaker to settle before resuming listening
                        time.sleep(0.8)
                    else:
                        # Reset interrupt flag for next speak
                        self.interrupt_requested = False
                        # Brief pause before listening again
                        time.sleep(0.2)
                        
                else:
                    logger.warning(f"Piper returned error code {result.returncode}")
                    stderr_text = result.stderr.decode(errors="ignore").strip()
                    if stderr_text:
                        logger.debug(f"Piper stderr: {stderr_text}")
                        self.log(f"🔇 TTS failed (piper): {stderr_text}")
                    else:
                        self.log(f"🔇 TTS failed: {text}")
                
                # Clean up temp file
                try:
                    os.unlink(temp_path)
                except:
                    pass
                
            except Exception as e:
                self.log(f"Piper TTS Error: {e}")
                logger.error(f"Piper TTS failed: {e}", exc_info=True)
            finally:
                # Ensure flags are reset
                self.is_speaking = False
                self.stop_vad_monitor()
                self.current_tts_process = None
                
                # Update dashboard: back to idle
                if hasattr(self, 'dashboard'):
                    self.dashboard.push_state(mode="idle")
    def process_conversation(self, raw_text):
        """Authoritative conversation router driven by INTENTS."""
        logger.debug(f"Processing conversation: {raw_text}")
        self.log(f"User: {raw_text}")
        text_lower = raw_text.lower().strip()

        # 1) Highest priority: confirmation continuations.
        if self.check_pending_confirmation(raw_text):
            return

        # 2) Explicit short-key resolver (e1/wr1/c1...).
        if self._handle_contextual_command(raw_text):
            return

        # 3) Context-follow-up resolver ("reply to that", "mark that handled").
        if self._route_by_context(raw_text, text_lower):
            return

        # 4) INTENTS table as single source of truth.
        intent_name, intent_cfg, handler = self._match_intent(raw_text)
        if intent_name and handler:
            logger.debug(f"Intent matched: {intent_name} -> {handler.__name__}")
            self._dispatch_intent(intent_name, intent_cfg, handler, raw_text)
            return

        # 5) Fallback to general LLM conversation.
        self.fallback_to_llm(raw_text)

    def cleanup_audio_resources(self):
        """Safely cleanup audio resources to prevent device lock."""
        logger.debug("Starting audio resource cleanup")
        try:
            # Stop VAD monitor thread first
            self.stop_vad_monitor()
            
            # Kill any active TTS process
            if self.current_tts_process:
                try:
                    self.current_tts_process.kill()
                    logger.debug("TTS process killed")
                except:
                    pass
                self.current_tts_process = None
            
            # Reset speaking flag
            self.is_speaking = False
            
            # Clean up recorder
            if self.recorder is not None:
                try:
                    if hasattr(self.recorder, 'stop'):
                        self.recorder.stop()
                        logger.debug("Recorder stopped")
                except Exception as e:
                    if "access violation" not in str(e).lower():
                        logger.warning(f"Error stopping recorder: {e}")
                try:
                    self.recorder.delete()
                    logger.debug("Recorder deleted")
                except Exception as e:
                    if "access violation" not in str(e).lower():
                        logger.warning(f"Error deleting recorder: {e}")
                self.recorder = None
                self.log("✓ Recorder cleaned up")
            
            # Clean up porcupine
            if self.porcupine is not None:
                try:
                    self.porcupine.delete()
                    logger.debug("Porcupine deleted")
                except Exception as e:
                    logger.warning(f"Error deleting porcupine: {e}")
                self.porcupine = None
                self.log("✓ Porcupine cleaned up")
            
            logger.info("Audio resources cleanup complete")
        except Exception as e:
            self.log(f"Cleanup Error: {e}")
            logger.error(f"Cleanup failed: {e}", exc_info=True)

    def should_skip_wake_word(self):
        """Check if we should skip wake word detection due to conversation mode."""
        # In conversation mode, always skip wake word - continuous listening enabled
        if self.conversation_mode:
            return True
        return False

    def run_wake_word_loop(self):
        logger.info("Wake word loop starting")
        try:
            # Create Porcupine instance
            logger.debug("Creating Porcupine instance...")
            logger.debug(f"Using access key: {PICOVOICE_KEY[:20]}...")
            self.porcupine = pvporcupine.create(access_key=PICOVOICE_KEY, keywords=['jarvis'])
            if self.porcupine is None:
                raise RuntimeError("Porcupine creation returned None")
            logger.info("✓ Porcupine created successfully")
            self.log("✓ Wake word engine initialized")
            
            # Create recorder
            logger.debug(f"Creating recorder with frame_length={self.porcupine.frame_length}")
            self.recorder = PvRecorder(device_index=-1, frame_length=self.porcupine.frame_length)
            if self.recorder is None:
                raise RuntimeError("Recorder creation returned None")
            
            # Log available devices
            devices = PvRecorder.get_available_devices()
            logger.info(f"Available audio devices: {devices}")
            logger.info(f"Using device index: -1 (default)")
            
            logger.debug("Starting recorder...")
            self.recorder.start()
            logger.info("✓ Recorder started successfully")
            
            self.status_var.set("Status: Monitoring...")
            self.log("🎤 Listening for wake word 'Jarvis'")
            
            frame_count = 0
            detection_attempts = 0

            while self.is_listening:
                self._refresh_command_capture_state()
                # Safety check - verify objects still exist
                if self.porcupine is None:
                    logger.error("Porcupine became None during loop - exiting")
                    self.log("⚠️  Error: Porcupine object lost")
                    break
                
                if self.recorder is None:
                    logger.error("Recorder became None during loop - exiting")
                    self.log("⚠️  Error: Recorder object lost")
                    break
                
                # Check if gaming mode was enabled
                if self.gaming_mode:
                    logger.info("Gaming mode detected - stopping wake word loop")
                    break
                
                # Check if microphone is muted
                if self.mic_muted:
                    logger.debug("Microphone muted - skipping audio processing")
                    time.sleep(0.1)
                    continue
                
                # Check if we should skip wake word detection (Conversation Mode)
                if self.should_skip_wake_word():
                    # Conversation mode - open mic, continuous listening
                    logger.debug("Entering continuous listening mode")
                    self.status_var.set("Status: 💬 Conversation Mode - Speak freely...")
                    
                    # Continuously listen for speech
                    transcribed_text = self.continuous_listen_and_transcribe()
                    
                    if transcribed_text:
                        self.log(f"You: {transcribed_text}")
                        # Process the conversation
                        self.process_conversation(transcribed_text)
                        # Immediately ready for next input
                        self.status_var.set("Status: 💬 Ready for next input...")
                        time.sleep(0.5)  # Brief pause
                    else:
                        # No speech detected, continue monitoring
                        time.sleep(0.1)
                    
                    continue
                
                try:
                    pcm = self.recorder.read()
                    frame_count += 1
                    detection_attempts += 1
                    
                    # Log every 500 frames (~10 seconds at 50Hz)
                    if frame_count % 500 == 0:
                        logger.debug(f"Processing audio: {frame_count} frames captured, listening active")
                    
                    keyword_index = self.porcupine.process(pcm)
                    
                    if keyword_index >= 0:
                        self.status_var.set("Status: Wake Word Heard!")
                        self.log("👂 Wake word detected!")
                        logger.info(f"Wake word detected (index: {keyword_index}) after {detection_attempts} frames")
                        detection_attempts = 0
                        self._start_command_capture()
                        if self.is_speaking:
                            self.interrupt_requested = True
                            logger.info("Wake word: interrupting active speech to prioritize command capture")
                        
                        # Update dashboard: switch to listening mode
                        if hasattr(self, 'dashboard'):
                            self.dashboard.push_state(mode="listening")
                        
                        # Audio handshake - play pre-generated "Yes?" audio
                        self.play_yes_audio()
                        
                        # Wait a moment for audio to finish
                        time.sleep(0.5)
                        
                        # Capture and transcribe user's command (VAD-based)
                        transcribed_text = self.listen_and_transcribe()
                        
                        if transcribed_text:
                            # Process the conversation
                            self.process_conversation(transcribed_text)
                            self._end_command_capture()
                        else:
                            self.log("⚠️  No command heard")
                            self.status_var.set("Status: Monitoring...")
                            self._end_command_capture()
                        
                except Exception as e:
                    logger.error(f"Error processing audio frame: {e}")
                    # Continue loop on frame processing errors
                    time.sleep(0.01)
                    
            logger.info(f"Wake word loop exiting normally (processed {frame_count} frames total)")
            
        except Exception as e:
            error_msg = f"Critical Error in wake word loop: {e}"
            self.log(error_msg)
            logger.error(error_msg)
            logger.error(f"Full traceback:\n{traceback.format_exc()}")
            self.status_var.set("Status: Error - Check Console")
        finally:
            self._end_command_capture()
            logger.debug("Wake word loop cleanup starting")
            self.cleanup_audio_resources()
    
    def setup_n8n_webhook(self):
        """Initialize Flask app for n8n webhook notifications."""
        self.flask_app = Flask(__name__)
        
        @self.flask_app.route('/jarvis/notify', methods=['POST'])
        def webhook_handler():
            try:
                notification = request.json
                logger.info(f"Received n8n webhook: {notification}")
                self.handle_n8n_webhook(notification)
                return jsonify({"status": "received"}), 200
            except Exception as e:
                logger.error(f"Webhook error: {e}")
                return jsonify({"error": str(e)}), 400
        
        @self.flask_app.route('/speak', methods=['POST'])
        def receive_speak():
            """Email notification endpoint (compatible with jarvis_main.py)."""
            try:
                data = request.get_json(force=True)
                
                # Extract email fields
                sender = data.get("sender", "Unknown")
                subject = data.get("subject", "No Subject")
                email_id = data.get("id")
                snippet = data.get("snippet", "")
                
                # DEBUG: Log payload when missing critical fields
                if sender == "Unknown" or subject == "No Subject":
                    logger.warning(f"Malformed email payload received: {data}")
                    logger.warning("Expected fields: 'sender', 'subject', 'id'")
                
                # Deduplicate by email ID
                if email_id:
                    # Clean old email IDs every hour
                    current_time = time.time()
                    if current_time - self.last_email_cleanup > 3600:
                        cutoff_time = current_time - 3600
                        self.seen_email_ids = {
                            eid: ts for eid, ts in self.seen_email_ids.items()
                            if ts > cutoff_time
                        }
                        self.last_email_cleanup = current_time
                    
                    # Check if we've seen this email in the last hour
                    if email_id in self.seen_email_ids:
                        logger.debug(f"Duplicate email notification ignored: {email_id}")
                        return jsonify({"status": "duplicate"}), 200
                    
                    # Mark email as seen
                    self.seen_email_ids[email_id] = current_time
                else:
                    logger.warning("Email notification received without ID - cannot deduplicate")
                
                # Clean sender for speech (extract just the name part)
                clean_sender = self.extract_sender_name(sender)
                # Also clean subject for special characters
                clean_subject = self.sanitize_for_speech(subject)
                
                # Format as n8n notification for consistent handling
                notification = {
                    "message": f"Sir, you have a new email from {clean_sender} regarding {clean_subject}.",
                    "priority": "high",
                    "source": "Email",
                    "metadata": {
                        "sender": sender,
                        "subject": subject,
                        "id": email_id
                    }
                }
                
                logger.info(f"Received email notification: {sender} - {subject}")
                self.handle_n8n_webhook(notification)
                return {"status": "success"}, 200
            except Exception as e:
                logger.error(f"Email webhook error: {e}")
                return {"error": str(e)}, 400
        
        # Start Flask in background thread (port 5001 to avoid conflict with dashboard on 5000)
        flask_thread = threading.Thread(target=lambda: self.flask_app.run(host='127.0.0.1', port=5001, debug=False), daemon=True)
        flask_thread.start()
        logger.info("✓ n8n webhook listener started on http://127.0.0.1:5001/jarvis/notify")
        logger.info("✓ Email webhook listener started on http://127.0.0.1:5001/speak")
    
    # ===== RELATIVE TIME PARSER =====
    def parse_relative_datetime(self, time_expr):
        """Parse relative time expressions into datetime objects.

        Handles: tomorrow [morning/afternoon/evening], this evening, tonight,
                 after lunch, in X minutes/hours, next week, day names,
                 later, this afternoon.

        Returns:
            (start_dt, end_dt) tuple, or (None, None) if no time found.
        """
        import re
        now = datetime.now()
        text = time_expr.lower().strip()

        # "in X minutes/hours/days"
        m = re.search(r'in\s+(\d+)\s+(minute|hour|day)s?', text)
        if m:
            amount = int(m.group(1))
            unit = m.group(2)
            delta = {'minute': timedelta(minutes=amount),
                     'hour': timedelta(hours=amount),
                     'day': timedelta(days=amount)}[unit]
            start_dt = now + delta
            return start_dt, start_dt + timedelta(hours=1)

        # Day-of-week names
        day_names = ['monday', 'tuesday', 'wednesday', 'thursday',
                     'friday', 'saturday', 'sunday']
        for i, day in enumerate(day_names):
            if day in text:
                days_ahead = (i - now.weekday()) % 7 or 7
                base = (now + timedelta(days=days_ahead)).replace(
                    second=0, microsecond=0)
                hour = 9
                if 'afternoon' in text:
                    hour = 14
                elif 'evening' in text:
                    hour = 19
                start_dt = base.replace(hour=hour, minute=0)
                return start_dt, start_dt + timedelta(hours=1)

        # tomorrow
        if 'tomorrow' in text:
            base = (now + timedelta(days=1)).replace(second=0, microsecond=0)
            hour = 9
            if 'afternoon' in text:
                hour = 14
            elif 'evening' in text or 'night' in text:
                hour = 19
            start_dt = base.replace(hour=hour, minute=0)
            return start_dt, start_dt + timedelta(hours=1)

        # this evening / tonight
        if 'this evening' in text or 'tonight' in text:
            start_dt = now.replace(hour=19, minute=0, second=0, microsecond=0)
            if start_dt <= now:
                start_dt += timedelta(days=1)
            return start_dt, start_dt + timedelta(hours=1)

        # after lunch
        if 'after lunch' in text:
            start_dt = now.replace(hour=13, minute=30, second=0, microsecond=0)
            if start_dt <= now:
                start_dt += timedelta(days=1)
            return start_dt, start_dt + timedelta(hours=1)

        # next week
        if 'next week' in text:
            start_dt = (now + timedelta(days=7)).replace(
                hour=9, minute=0, second=0, microsecond=0)
            return start_dt, start_dt + timedelta(hours=1)

        # later / this afternoon
        if 'later' in text or 'this afternoon' in text:
            if now.hour < 14:
                start_dt = now.replace(hour=14, minute=0, second=0, microsecond=0)
            else:
                start_dt = now + timedelta(hours=2)
                start_dt = start_dt.replace(second=0, microsecond=0)
            return start_dt, start_dt + timedelta(hours=1)

        return None, None

    # ===== PENDING CONFIRMATION CHECK =====
    def check_pending_confirmation(self, text):
        """Check if user is responding to a pending action requiring confirmation.

        Returns True if the input was fully handled (caller should return).
        """
        text_lower = text.lower().strip()

        confirm_words = ['yes', 'yeah', 'yep', 'send it', 'send that',
                         'go ahead', 'do it', 'ok', 'okay', 'confirm',
                         'correct', 'sure', 'please']
        deny_words = ['no', 'nope', 'cancel', "don't", 'dont',
                      'stop', 'abort', 'wait', 'hold on', 'actually']

        # --- Pending email reply ---
        if self.pending_reply:
            if any(w in text_lower for w in confirm_words):
                rd = self.pending_reply
                self.pending_reply = None
                success = self.reply_to_email(rd['email_id'], rd['reply_text'])
                if success:
                    msg = f"Reply sent to {rd['sender_name']}."
                    self.log(f"[ok] {msg}")
                    self.speak_with_piper(msg)
                    self.log_vault_action(
                        "email_replied",
                        f"Replied to {rd['sender']}",
                        metadata={
                            "recipient": rd['sender'],
                            "message_preview": rd['reply_text'][:100],
                            "timestamp": datetime.now().isoformat()
                        })
                    self.last_intent = "email"
                else:
                    self.speak_with_piper("I had trouble sending that reply.")
                return True

            if any(w in text_lower for w in deny_words):
                self.pending_reply = None
                self.speak_with_piper("Reply cancelled.")
                self.log("Reply cancelled by user.")
                return True

            # Ambiguous: remind user there's a pending action.
            self.speak_with_piper(
                f"Just to confirm, shall I send that reply to "
                f"{self.pending_reply['sender_name']}?")
            return True

        # --- Pending calendar event (waiting for time) ---
        if self.pending_calendar_title:
            start_dt, end_dt = self.parse_relative_datetime(text)
            if start_dt:
                title = self.pending_calendar_title
                self.pending_calendar_title = None
                event = self.create_calendar_event(title, start_dt, end_dt)
                if event:
                    new_time = start_dt.strftime(
                        '%A %d %b at %I:%M %p').lstrip('0')
                    msg = f"Done. I've booked {title} for {new_time}."
                    self.speak_with_piper(msg)
                    self.add_to_context("User", text)
                    self.add_to_context("Jarvis", msg)
                    self.last_intent = "calendar"
                    self.log_vault_action(
                        "calendar_created", f"Created: {title} at {new_time}")
                    cal_text = self.get_calendar()
                    self.dashboard.push_focus("docs", "Calendar", cal_text)
                else:
                    self.speak_with_piper("I had trouble creating that event.")
                return True

            if any(w in text_lower for w in deny_words):
                self.pending_calendar_title = None
                self.speak_with_piper("Booking cancelled.")
                return True

        return False

    # ===== TASK / REMINDER SYSTEM =====
    def add_task(self, description, remind_at=None):
        """Add a task to the task list with an optional timed reminder."""
        task = {
            'id': int(time.time() * 1000),
            'description': description,
            'created': datetime.now().isoformat(),
            'remind_at': remind_at.isoformat() if remind_at else None,
            'done': False,
            'reminded': False
        }
        self.tasks.append(task)
        self.memory['tasks'] = self.tasks
        self.save_memory()
        self.log_vault_action(
            'task_created',
            f"Task added: {description}",
            metadata={'task_id': task['id'], 'remind_at': task['remind_at']})
        return task

    def list_tasks(self, show_done=False):
        """Return a formatted string of pending (or all) tasks."""
        items = self.tasks if show_done else [t for t in self.tasks if not t['done']]
        if not items:
            return "No pending tasks."
        lines = []
        for i, t in enumerate(items, 1):
            remind_str = ""
            if t.get('remind_at'):
                try:
                    rdt = datetime.fromisoformat(t['remind_at'])
                    remind_str = f"  [Due: {rdt.strftime('%a %d %b %I:%M %p')}]"
                except Exception:
                    pass
            done_str = " [done]" if t.get('done') else ""
            lines.append(f"{i}. {t['description']}{remind_str}{done_str}")
        return "\n".join(lines)

    def mark_task_done(self, query):
        """Mark a task done by 1-based index or partial description match.

        Returns the task description string if found, else None.
        """
        import re
        active = [t for t in self.tasks if not t['done']]
        # Numeric index
        m = re.search(r'\b(\d+)\b', query)
        if m:
            idx = int(m.group(1)) - 1
            if 0 <= idx < len(active):
                active[idx]['done'] = True
                self.memory['tasks'] = self.tasks
                self.save_memory()
                self.log_vault_action(
                    'task_completed',
                    f"Completed: {active[idx]['description']}")
                return active[idx]['description']
        # Keyword match
        q_lower = query.lower()
        for task in active:
            words = [w for w in q_lower.split() if len(w) > 3]
            if words and any(w in task['description'].lower() for w in words):
                task['done'] = True
                self.memory['tasks'] = self.tasks
                self.save_memory()
                self.log_vault_action(
                    'task_completed', f"Completed: {task['description']}")
                return task['description']
        return None

    def reminder_scheduler_loop(self):
        """Background thread: fire due reminders and process notification queue every 30 seconds."""
        IDLE_THRESHOLD = 60  # seconds
        while True:
            try:
                now = datetime.now()
                for task in self.tasks:
                    if task.get('done') or task.get('reminded') or not task.get('remind_at'):
                        continue
                    try:
                        remind_dt = datetime.fromisoformat(task['remind_at'])
                        seconds_until = (remind_dt - now).total_seconds()
                        if 0 <= seconds_until < 60:
                            task['reminded'] = True
                            task['remind_at'] = None
                            self.memory['tasks'] = self.tasks
                            self.save_memory()
                            msg = f"Sir, reminder: {task['description']}"
                            self.log(f"Reminder fired: {msg}")
                            if not self.gaming_mode:
                                self.speak_with_piper(msg)
                            else:
                                self.notification_queue.append({
                                    'source': 'Reminder',
                                    'message': msg,
                                    'timestamp': datetime.now().isoformat(),
                                    'metadata': {}
                                })
                    except Exception:
                        pass
            except Exception as e:
                logger.error(f"Reminder scheduler error: {e}")

            # Idle-time alert for priority notifications.
            try:
                is_idle = (time.time() - self.last_interaction_time) > IDLE_THRESHOLD
                if is_idle and not self.is_speaking and not self.gaming_mode:
                    with self.queue_lock:
                        # Find first unannounced high-priority notification.
                        priority_item = next(
                            (item for item in self.notification_queue
                             if item.get('priority') == 'HIGH' and not item.get('announced')),
                            None
                        )

                        if priority_item:
                            # Mark as announced to prevent re-triggering.
                            priority_item['announced'] = True

                            # Formulate and speak the prompt.
                            short_key = priority_item.get('short_key', 'a notification')
                            sender = self.extract_sender_name(
                                priority_item.get('metadata', {}).get('sender', 'an unknown source')
                            )
                            prompt = (
                                f"Sir, you have a priority email [{short_key}] from "
                                f"{sender}. Shall I display it?"
                            )

                            # Reset idle timer to avoid spamming alerts.
                            self.last_interaction_time = time.time()

                            self.log(f"Idle alert: {prompt}")
                            self.speak_with_piper(prompt)
            except Exception as e:
                logger.error(f"Idle-time alert processing error: {e}")

            try:
                if self.notification_queue and not self.is_speaking:
                    logger.debug("Scheduler: processing notification queue")
                    self.process_notification_queue(context="idle")
            except Exception as e:
                logger.error(f"Notification queue processing error in scheduler: {e}")

            time.sleep(30)

    def _handle_list_tasks(self, user_request):
        """Sub-handler for listing tasks."""
        task_text = self.list_tasks()
        reply = ("Here are your pending tasks:\n" + task_text
                 if task_text != "No pending tasks."
                 else "You have no pending tasks.")
        self.speak_with_piper(reply)
        self.add_to_context("User", user_request)
        self.add_to_context("Jarvis", reply)
        self.last_intent = "task"
        self.dashboard.push_focus("docs", "Task List", task_text)
        self.log_vault_action("tasks_listed", "Listed pending tasks")

    def _handle_complete_task(self, user_request):
        """Sub-handler for completing tasks."""
        desc = self.mark_task_done(user_request)
        if desc:
            msg = f"Done. I've marked '{desc}' as complete."
            self.speak_with_piper(msg)
            self.add_to_context("User", user_request)
            self.add_to_context("Jarvis", msg)
            self.last_intent = "task"
            self.dashboard.push_focus("docs", "Task List", self.list_tasks())
        else:
            self.speak_with_piper(
                "I couldn't find that task. "
                "You can say the number or part of the description.")

    def _handle_recall_task(self, user_request):
        """Sub-handler for recalling past tasks/actions."""
        text = user_request.lower()
        recall_match = re.search(
            r'\b(?:did|have)\s+(?:i|you|we)\s+(?:ever\s+)?(.+?)(?:\?|$)',
            text)
        if not recall_match:
            return

        keyword = recall_match.group(1).strip()
        done_tasks = [t for t in self.tasks
                      if t.get('done') and keyword in t['description'].lower()]
        action_hits = self.memory_index.search_by_keyword(keyword, limit=3)
        if done_tasks:
            msg = f"Yes - '{done_tasks[0]['description']}' was marked done."
        elif action_hits:
            a = action_hits[0]
            msg = (f"I logged this: {a.get('description', 'an action')} "
                   f"on {a.get('timestamp', '')[:10]}.")
        else:
            pending = [t for t in self.tasks
                       if not t.get('done') and keyword in t['description'].lower()]
            if pending:
                msg = f"It's still on your list: {pending[0]['description']}"
            else:
                msg = "I don't have any record of that, Sir."
        self.speak_with_piper(msg)
        self.add_to_context("User", user_request)
        self.add_to_context("Jarvis", msg)
        self.last_intent = "task"

    def _handle_add_task(self, user_request):
        """Sub-handler for adding a new task."""
        task_desc = None
        m = re.search(
            r'(?:remind(?:er)?\s+(?:me\s+)?(?:to\s+)?|remember\s+to\s+|'
            r'don\'t\s+forget\s+(?:to\s+)?|note\s+(?:to\s+)?(?:self\s+)?)'
            r'(.+?)(?:\s+(?:in\s+\d|\bat\b|\bon\b|tomorrow|tonight|this|next)|$)',
            user_request, re.IGNORECASE)
        if m:
            task_desc = m.group(1).strip()
        if not task_desc:
            s = re.search(r'remind(?:er)?\s+(?:me\s+)?(?:to\s+)?(.+)',
                          user_request, re.IGNORECASE)
            if s:
                task_desc = s.group(1).strip()
        if not task_desc:
            task_desc = user_request.strip()

        remind_at, _ = self.parse_relative_datetime(user_request)
        self.add_task(task_desc, remind_at)

        if remind_at:
            time_str = remind_at.strftime('%A at %I:%M %p').lstrip('0')
            msg = f"Noted. I'll remind you to {task_desc} on {time_str}."
        else:
            msg = f"Added to your list: {task_desc}."

        self.speak_with_piper(msg)
        self.add_to_context("User", user_request)
        self.add_to_context("Jarvis", msg)
        self.last_intent = "task"
        self.dashboard.push_focus("docs", "Task List", self.list_tasks())

    def handle_task_request(self, user_request):
        """Refactored task handler. Routes to sub-handlers for specific actions."""
        text = user_request.lower()

        # --- LIST ---
        list_words = ["what's on my list", "show my tasks", "what tasks",
                      "list tasks", "pending tasks", "my reminders",
                      "show reminders", "what do i need to do",
                      "what have i got"]
        if any(w in text for w in list_words):
            self._handle_list_tasks(user_request)
            return

        # --- COMPLETE ---
        complete_words = ['done', 'complete', 'finished', 'mark',
                          'tick off', 'crossed off', 'check off']
        if any(w in text for w in complete_words):
            self._handle_complete_task(user_request)
            return

        # --- RECALL ---
        if re.search(r'\b(?:did|have)\s+(?:i|you|we)\s+(?:ever\s+)?', text):
            self._handle_recall_task(user_request)
            return

        # --- ADD / CREATE (default action) ---
        self._handle_add_task(user_request)

if __name__ == "__main__":
    # Check for required credential files before starting
    check_credentials()
    
    app = None
    
    def signal_handler(sig, frame):
        """Handle Ctrl+C gracefully."""
        logger.info(f"Signal {sig} received")
        print("\n\nInterrupt received. Shutting down gracefully...")
        if app:
            app.is_listening = False
            try:
                app.on_closing()
            except Exception as e:
                pass
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    if hasattr(signal, 'SIGTERM'):
        signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        app = JarvisGT2()
        logger.info("Starting Jarvis (headless mode)...")
        
        # Keep application alive - dashboard handles UI by connecting to ws://localhost:5000
        # Dashboard should be running: npm run dev in GUI/Cyber-Grid-Dashboard
        logger.info("Jarvis running. Press Ctrl+C to stop.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Keyboard interrupt received")
            print("\n\nShutting down gracefully...")
    except Exception as e:
        logger.error(f"Unexpected error in main: {e}", exc_info=True)
        print(f"\nError: {e}")
    finally:
        print("Jarvis GT2 stopped.")

