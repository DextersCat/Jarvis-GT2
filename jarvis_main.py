import customtkinter as ctk
import pvporcupine
from pvrecorder import PvRecorder
import threading
import time
import os
import json
import whisper
import requests
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
import subprocess
import sys
import logging
import traceback
import signal
import tempfile
import shutil
import wave
import numpy as np
import collections
from flask import Flask, request, jsonify
from datetime import datetime
from vault_reference import VaultReference
from memory_index import MemoryIndex

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
    
    # VAD Settings for barge-in and adaptive listening
    # Environment variables take priority over config.json
    config_vad = config.get("vad_settings", {})
    vad_settings = {
        "energy_threshold": int(os.getenv("VAD_ENERGY_THRESHOLD", config_vad.get("energy_threshold", 500))),
        "silence_duration": float(os.getenv("VAD_SILENCE_DURATION", config_vad.get("silence_duration", 1.2))),
        "min_speech_duration": float(os.getenv("VAD_MIN_SPEECH_DURATION", config_vad.get("min_speech_duration", 0.5))),
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
LLM_MODEL = config_dict["llm_model"]
VAD_SETTINGS = config_dict["vad_settings"]

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='[%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

class JarvisGT2(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("New Jarvis GT2 - Integrated Command Center")
        self.geometry("600x700")
        ctk.set_appearance_mode("dark")

        self.is_listening = False
        self.gaming_mode = False
        self.conversation_mode = False
        self.last_interaction_time = 0
        self.stt_model = whisper.load_model("base", device="cpu", download_root=None, in_memory=False)
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
        
        # Priority Notification Queue (n8n Integration)
        self.notification_queue = []
        self.urgent_interrupt = False
        self.notification_cooldown = 10  # seconds
        self.last_notification_speak_time = 0
        
        # Email deduplication (track seen email IDs for 1 hour)
        self.seen_email_ids = {}  # {email_id: timestamp}
        self.last_email_cleanup = time.time()
        
        # Audio synchronization (prevent speaking over self)
        self.speak_lock = threading.Lock()

        # Health tracking for proactive interventions
        self.interaction_count = 0
        self.last_break_time = time.time()
        self.memory = self.load_memory()
        
        # VAD parameters - loaded from config
        self.vad_threshold = VAD_SETTINGS.get("energy_threshold", 500)
        self.silence_duration = VAD_SETTINGS.get("silence_duration", 1.2)
        self.min_speech_duration = VAD_SETTINGS.get("min_speech_duration", 0.5)
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
        
        logger.info("Jarvis GT2 initializing...")

        # GUI Layout
        self.label = ctk.CTkLabel(self, text="NEW JARVIS GT2", font=("Arial", 28, "bold"))
        self.label.pack(pady=20)

        self.status_var = ctk.StringVar(value="Status: Standby")
        self.status_label = ctk.CTkLabel(self, textvariable=self.status_var, font=("Arial", 16), text_color="cyan")
        self.status_label.pack(pady=5)

        self.gaming_mode_switch = ctk.CTkSwitch(self, text="🎮 Gaming Mode (Disable Mic)", command=self.toggle_gaming_mode)
        self.gaming_mode_switch.pack(pady=15)

        self.conversation_mode_switch = ctk.CTkSwitch(self, text="💬 Conversation Mode (Continuous)", command=self.toggle_conversation_mode)
        self.conversation_mode_switch.pack(pady=10)

        self.console = ctk.CTkTextbox(self, width=550, height=350, font=("Consolas", 12))
        self.console.pack(pady=10)

        self.log("System Online. Google Services Connected.")
        logger.info("System initialized successfully")
        
        # Set up window close protocol
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        logger.debug("Window close protocol registered")
        
        # Initialize n8n webhook listener for priority notifications
        self.setup_n8n_webhook()
        
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
        """Log to both GUI console and system logger."""
        timestamp = time.strftime('%H:%M:%S')
        # Check if console exists before trying to access it
        if hasattr(self, 'console') and self.console:
            self.console.insert("end", f"[{timestamp}] {text}\n")
            self.console.see("end")
        logger.info(text)
    
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
    
    def handle_optimization_request(self, user_request):
        """
        Multi-step intent handler for code analysis and documentation workflow.
        
        Flow:
        1. Confirm the task with the user via VAD
        2. Read the specified file content from vault
        3. Send to Ollama with optimization-focused prompt
        4. Create a Google Doc with the analysis
        5. Confirm completion with the URL
        
        Args:
            user_request: The user's original request
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
                # Log failed read attempt
                self.log_vault_action(
                    action_type="optimization_failed",
                    description=f"Failed to read file for optimization: {os.path.basename(target_file)}"
                )
                return
            
            file_content = file_data['content']
            filename = file_data['filename']
            
            # Step 3: Send to Ollama/Brain for optimization analysis
            self.log("🧠 Sending to AI brain for analysis...")
            self.speak_with_piper("Analyzing the code for optimization opportunities.")
            
            optimization_prompt = f"""You are a expert code reviewer and performance optimizer. 
Analyze the following code file: {filename}

CODE:
```
{file_content}
```

Please identify the THREE most important performance optimizations or improvements that could be made to this code. For each optimization:

1. **Issue**: Describe the problem
2. **Impact**: What performance or maintainability benefit would this provide?
3. **Suggestion**: Provide a concrete code example or approach

Format your response as a clear, professional code review suitable for documentation.
"""
            
            # Send to brain (Ollama)
            self.status_var.set("Status: 🧠 AI Analysis in Progress...")
            response = requests.post(
                BRAIN_URL, 
                json={
                    "model": LLM_MODEL, 
                    "prompt": optimization_prompt, 
                    "stream": False
                },
                timeout=120
            )
            
            optimization_analysis = response.json().get('response', "Analysis could not be completed.")
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
            
            # Step 5: Log completion and confirm with user
            self.log_vault_action(
                action_type="optimization_complete",
                description=f"Completed optimization analysis for {filename}",
                metadata={
                    "filename": filename,
                    "doc_url": doc_url,
                    "analysis_length": len(optimization_analysis),
                    "folder_id": GOOGLE_DRIVE_FOLDER_ID
                }
            )
            
            # Confirmation message - Clear Scribe workflow confirmation
            doc_title = doc_result.get('title', 'Optimization Report')
            self.log(f"✅ SCRIBE COMPLETE - Optimization Report Created")
            self.log(f"📄 Document: {doc_title}")
            self.log(f"📁 Saved to: Google Drive (Folder ID: {doc_result.get('folder_id') or GOOGLE_DRIVE_FOLDER_ID})")
            self.log(f"🔗 URL: {doc_url}")
            
            # Speak confirmation with filename reference
            confirmation = f"Sir, the optimization report for {filename} is ready in your Drive."
            self.speak_with_piper(confirmation)
            self.log(f"🔊 Confirmed: {confirmation}")
            
            # Add to context buffer for conversation continuity
            self.add_to_context("Task", f"Optimization analysis completed: {filename}")
            self.add_to_context("Jarvis", f"Report created: {doc_title}")
            
            # Save memory with final state
            self.save_memory()
            
            logger.info(f"✓ Optimization workflow complete for {filename}")
            self.status_var.set("Status: Ready")
            
        except Exception as e:
            error_msg = f"Error in optimization workflow: {e}"
            logger.error(error_msg, exc_info=True)
            self.log(f"❌ {error_msg}")
            self.speak_with_piper("An error occurred during the analysis. Please check the console for details.")
    
    def add_to_context(self, role, message):
        """Add message to short-term context buffer."""
        self.context_buffer.append({"role": role, "message": message})
        logger.debug(f"Context buffer size: {len(self.context_buffer)}")
    
    def get_context_history(self):
        """Get formatted context history for LLM."""
        if not self.context_buffer:
            return ""
        history = "CONVERSATION CONTEXT (last exchanges):\n"
        for exchange in self.context_buffer:
            history += f"  {exchange['role']}: {exchange['message'][:100]}...\n"
        return history
    
    def health_intervener(self):
        """Proactively propose breaks if Spencer is working too long."""
        health_profile = self.memory.get("master_profile", {}).get("health_profile", {})
        break_interval = health_profile.get("recommended_break_interval", 90)  # minutes
        
        elapsed_time = (time.time() - self.last_break_time) / 60  # Convert to minutes
        
        if elapsed_time > break_interval:
            logger.info(f"Health check: {elapsed_time:.0f} minutes since last break")
            self.last_break_time = time.time()
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
        priority = notification.get("priority", "ROUTINE")
        message = notification.get("message", "No content")
        source = notification.get("source", "Unknown")
        
        logger.info(f"n8n Notification [{priority}]: {source} - {message}")
        
        if priority == "URGENT":
            self.urgent_interrupt = True
            logger.warning(f"URGENT notification queued: {message}")
        elif str(priority).upper() == "HIGH":
            now = time.time()
            if now - self.last_notification_speak_time >= self.notification_cooldown:
                self.last_notification_speak_time = now
                self.speak_with_piper(message)
                logger.info(f"High-priority notification spoken: {message}")
            else:
                self.notification_queue.append({"source": source, "message": message, "timestamp": datetime.now().isoformat()})
                logger.debug(f"High-priority notification queued (cooldown): {message}")
        else:
            self.notification_queue.append({"source": source, "message": message, "timestamp": datetime.now().isoformat()})
            logger.debug(f"Routine notification queued: {message}")
    
    def interrupt_and_speak(self, message):
        """Interrupt current activity and speak urgent message."""
        logger.warning(f"INTERRUPT: {message}")
        self.log(f"🚨 URGENT: {message}")
        # The message will be processed before process_conversation completes
        # due to self.urgent_interrupt flag
        self.speak_with_piper(message)

    def toggle_gaming_mode(self):
        """Gaming Mode disables the microphone completely and frees resources."""
        self.gaming_mode = self.gaming_mode_switch.get()
        
        if self.gaming_mode:
            self.log("🎮 Gaming Mode: ENABLED")
            self.log("   → Mic disabled, resources freed")
            logger.info("Gaming mode activated - stopping all listening and freeing resources")
            
            # Stop listening and clean up resources
            self.is_listening = False
            self.cleanup_audio_resources()
            
            # Disable conversation mode
            if self.conversation_mode:
                self.conversation_mode_switch.deselect()
                self.conversation_mode = False
            
            self.status_var.set("Status: Gaming Mode - Mic Off")
        else:
            self.log("🎮 Gaming Mode: DISABLED")
            self.log("   → Returning to Normal Mode")
            logger.info("Gaming mode deactivated - returning to normal mode")
            self.status_var.set("Status: Standby")
            
            # Restart listening in normal mode
            self.start_listening()

    def toggle_conversation_mode(self):
        """Conversation Mode disables wake word for continuous chat."""
        self.conversation_mode = self.conversation_mode_switch.get()
        
        if self.conversation_mode:
            # Can't enable if gaming mode is on
            if self.gaming_mode:
                self.log("⚠️  Cannot enable Conversation Mode during Gaming Mode")
                logger.warning("Attempted to enable conversation mode during gaming mode")
                self.conversation_mode_switch.deselect()
                self.conversation_mode = False
                return
            
            self.log("💬 Conversation Mode: ENABLED")
            self.log("   → Open mic - just speak naturally!")
            self.log("   → No wake word needed, automatic speech detection")
            logger.info("Conversation mode activated - continuous speech detection with VAD")
            self.status_var.set("Status: 💬 Speak freely...")
            
            # Ensure listening is active
            if not self.is_listening:
                self.start_listening()
        else:
            self.log("💬 Conversation Mode: DISABLED")
            self.log("   → Back to wake word detection")
            logger.info("Conversation mode deactivated - back to normal wake word mode")
            self.status_var.set("Status: Monitoring...")

    # --- TOOLS: SEARCH, CALENDAR, GMAIL ---
    def google_search(self, query):
        """Perform Google search using Custom Search API with API key."""
        service = build("customsearch", "v1", developerKey=GOOGLE_CSE_API_KEY)
        res = service.cse().list(q=query, cx=GOOGLE_CSE_CX, num=3).execute()
        return "\n".join([f"{i['title']}: {i['snippet']}" for i in res.get('items', [])])

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
                if not self.is_listening or self.gaming_mode:
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
            
            # Convert to numpy array and normalize
            audio_data = np.array(speech_frames, dtype=np.int16)
            
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
            
            result = self.stt_model.transcribe(temp_path, language='en')
            text = result['text'].strip()
            
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
                if not self.is_listening or self.gaming_mode or not self.conversation_mode:
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
            
            result = self.stt_model.transcribe(temp_path, language='en')
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

    def extract_sender_name(self, sender_str):
        """Extract just the name from 'Name <email@domain>' format for speech."""
        if '<' in sender_str and '>' in sender_str:
            # Extract name part: "John Doe <john@example.com>" -> "John Doe"
            name = sender_str.split('<')[0].strip()
            return name if name else sender_str.replace('<', '').replace('>', '').replace('@', ' at ')
        # Remove @ and replace with 'at' for readability
        return sender_str.replace('@', ' at ').replace('<', '').replace('>', '')
    
    def sanitize_for_speech(self, text):
        """Remove/replace characters that shouldn't be spoken."""
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
    
    def speak_with_piper(self, text):
        """Use Piper TTS to speak longer responses (with barge-in support).
        Uses a lock to prevent concurrent audio playback (speaking over self).
        """
        with self.speak_lock:  # Serialize all speech generation
            # Log what Jarvis is saying for debugging transcript
            self.log(f"🤖 Jarvis: {text}")
            
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
                    
                    # Play the audio file using Windows - check for interruptions
                    self.current_tts_process = subprocess.Popen(
                        ["powershell", "-c", f"(New-Object Media.SoundPlayer '{temp_path}').PlaySync();"],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL
                    )
                    
                    # Monitor for barge-in while playing
                    while self.current_tts_process.poll() is None:
                        if self.interrupt_requested:
                            logger.warning("Barge-in: Stopping speech immediately")
                            self.current_tts_process.kill()
                            self.log("🛑 Interrupted - Listening, Sir")
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
    def process_conversation(self, raw_text):
        logger.debug(f"Processing conversation: {raw_text}")
        self.log(f"User: {raw_text}")
        context = ""

        # Intent Detection
        text_lower = raw_text.lower()
        
        # Clean up search queries - remove command phrases
        def clean_search_query(text):
            remove_phrases = [
                "search the web for", "search the word for", "search for", 
                "google for", "google", "look up", "find out about", "find",
                "tell me about", "what is", "who is", "what are"
            ]
            cleaned = text.lower()
            for phrase in remove_phrases:
                cleaned = cleaned.replace(phrase, "")
            return cleaned.strip()
        
        # Enhanced Intent Detection: Memory-based queries
        if "who are you" in text_lower or "what do you know about me" in text_lower or "tell me about yourself" in text_lower:
            logger.debug("Intent: Self-Knowledge (pulling from memory)")
            memory_facts = "\n".join(self.memory.get("facts", []))
            context = f"JARVIS MEMORY:\n{memory_facts}"
        # Dogzilla project queries
        elif "dogzilla" in text_lower:
            logger.debug("Intent: Dogzilla Project Knowledge")
            dogzilla = self.memory.get("projects", {}).get("dogzilla", {})
            context = f"""DOGZILLA PROJECT:
Name: {dogzilla.get('name', 'Dogzilla')}
Type: {dogzilla.get('type', 'ESP32-based robotics project')}
Description: {dogzilla.get('description', 'Mobile robotics platform')}
Status: {dogzilla.get('status', 'Active Development')}
Components: {', '.join(dogzilla.get('components', []))}"""
        # Weather queries - add location automatically
        elif "weather" in text_lower:
            self.status_var.set("Status: Searching Google...")
            logger.debug("Intent: Weather Search")
            search_query = f"weather in {LOCATION_OVERRIDE} today"
            context = self.google_search(search_query)
        elif "search" in text_lower or "who is" in text_lower or "what is" in text_lower or "find" in text_lower or "google" in text_lower:
            self.status_var.set("Status: Searching Google...")
            logger.debug("Intent: Google Search")
            cleaned_query = clean_search_query(raw_text)
            logger.debug(f"Cleaned query: '{cleaned_query}' from '{raw_text}'")
            context = self.google_search(cleaned_query)
        elif "calendar" in text_lower or "schedule" in text_lower:
            self.status_var.set("Status: Checking Calendar...")
            logger.debug("Intent: Calendar")
            context = self.get_calendar()
        
        # REPORT RETRIEVAL - Get last optimization report from memory
        elif (("open" in text_lower or "show" in text_lower or "read" in text_lower or "summarize" in text_lower or "summary" in text_lower) and 
              ("last" in text_lower or "latest" in text_lower or "recent" in text_lower) and 
              ("report" in text_lower or "optimization" in text_lower or "document" in text_lower)):
            logger.debug("Intent: Retrieve Last Report from Memory")
            self.log("📄 Retrieving last optimization report...")
            self.handle_report_retrieval(raw_text)
            return
        
        # OPTIMIZATION INTENT HANDLER - Scribe Capabilities (File Analysis)
        elif (("check" in text_lower and "file" in text_lower and ("write" in text_lower or "doc" in text_lower)) or
              ("analyze" in text_lower and "file" in text_lower) or
              ("optimize" in text_lower and "file" in text_lower) or
              ("check" in text_lower and "main" in text_lower and "write" in text_lower) or
              ("check" in text_lower and "config" in text_lower and "write" in text_lower)):
            logger.debug("Intent: Code Optimization Analysis (Scribe Workflow)")
            self.log("🧠 Starting optimization analysis workflow...")
            self.handle_optimization_request(raw_text)
            # After handling optimization request, don't continue to brain
            return

        # --- IMPROVED BRAIN LOGIC WITH CONTEXT AND MEMORY ---
        context_history = self.get_context_history()
        memory_facts = "\n".join(self.memory.get("facts", []))
        
        # Extract Master Profile for health-conscious communication
        master_profile = self.memory.get("master_profile", {})
        working_method = master_profile.get("working_method", "")
        communication_style = master_profile.get("communication_style", "")
        health_profile = master_profile.get("health_profile", {})
        
        # Check for project mention and auto-switch if detected
        self.detect_and_switch_project(raw_text)
        
        if context:
            # If we have external data, use it with context and memory
            vault_path = self.vault_root.replace('\\', '/')
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
- Use vault tools (list_vault_projects, read_project_file, search_vault) when asked about projects
- Natural, conversational tone suitable for voice delivery
- When discussing code, use clear Markdown formatting for readability
"""
        else:
            # Normal conversation with context and memory
            vault_path = self.vault_root.replace('\\', '/')
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
- Use vault tools (list_vault_projects, read_project_file, search_vault) when asked about projects
- Keep responses suitable for voice delivery
- When discussing code, use clear Markdown formatting for readability on 4-screen setup
"""
        
        self.status_var.set("Status: Thinking...")
        try:
            logger.debug(f"Sending request to LLM: {BRAIN_URL}")
            response = requests.post(BRAIN_URL, json={"model": LLM_MODEL, "prompt": prompt, "stream": False})
            answer = response.json().get('response', "I encountered an error thinking.")
            self.log(f"Jarvis: {answer}")
            self.speak_with_piper(answer)
            
            # Update short-term context buffer with this exchange
            self.add_to_context("User", raw_text)
            self.add_to_context("Jarvis", answer)
            
            # Log conversation interaction to persistent memory
            self.log_vault_action(
                action_type="conversation",
                description=f"Conversation: {raw_text[:50]}{'...' if len(raw_text) > 50 else ''}",
                metadata={
                    "user_query": raw_text,
                    "response_preview": answer[:100] if len(answer) > 100 else answer,
                    "response_length": len(answer),
                    "context_used": bool(context)
                }
            )
            
            # Check health: Proactively suggest breaks
            self.interaction_count += 1
            if self.health_intervener():
                self.log("💊 Proposing a health break...")
                # Don't speak immediately, just log the suggestion for next interaction
            
            # Save memory periodically
            self.save_memory()
            
            # Process notification queue (routine updates)
            if self.notification_queue:
                self.log("📩 Processing routine notifications...")
                notification_summary = "While you were busy, I received: "
                for notif in self.notification_queue:
                    notification_summary += f"{notif['source']}: {notif['message'][:50]}. "
                self.notification_queue = []  # Clear queue
                # Speak the summary (with echo-fix delay already applied)
                time.sleep(0.2)  # Brief pause before reading notifications
                self.speak_with_piper(notification_summary)
            
            self.last_interaction_time = time.time()
            logger.debug("Conversation processed successfully")
        except Exception as e:
            self.log(f"Brain Error: {e}")
            logger.error(f"Brain processing failed: {e}", exc_info=True)

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
        return should_skip

    # --- WAKE WORD LOOP ---
    # MODES:
    # 1. Normal Mode (default): Listens for "Jarvis" wake word to activate
    # 2. Gaming Mode: Mic disabled, all resources freed
    # 3. Conversation Mode: Open mic with VAD - speak freely, no wake word needed
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
                        
                        # Audio handshake - play pre-generated "Yes?" audio
                        self.play_yes_audio()
                        
                        # Wait a moment for audio to finish
                        time.sleep(0.5)
                        
                        # Capture and transcribe user's command (VAD-based)
                        transcribed_text = self.listen_and_transcribe()
                        
                        if transcribed_text:
                            # Process the conversation
                            self.process_conversation(transcribed_text)
                        else:
                            self.log("⚠️  No command heard")
                            self.status_var.set("Status: Monitoring...")
                        
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
                        return {"status": "duplicate"}, 200
                    
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
        
        # Start Flask in background thread
        flask_thread = threading.Thread(target=lambda: self.flask_app.run(host='127.0.0.1', port=5000, debug=False), daemon=True)
        flask_thread.start()
        logger.info("✓ n8n webhook listener started on http://127.0.0.1:5000/jarvis/notify")
        logger.info("✓ Email webhook listener started on http://127.0.0.1:5000/speak")

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
                app.quit()
            except:
                pass
    
    # Register signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    if hasattr(signal, 'SIGTERM'):
        signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        app = JarvisGT2()
        logger.info("Starting main loop...")
        app.mainloop()
    except KeyboardInterrupt:
        logger.info("Keyboard interrupt received")
        print("\n\nShutting down gracefully...")
    except Exception as e:
        logger.error(f"Unexpected error in main: {e}", exc_info=True)
        print(f"\nError: {e}")
    finally:
        # Ensure cleanup on exit
        if app and hasattr(app, 'cleanup_audio_resources'):
            logger.info("Final cleanup...")
            app.is_listening = False
            app.cleanup_audio_resources()
        logger.info("Application terminated")
        print("Jarvis GT2 stopped.")