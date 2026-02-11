#!/usr/bin/env python3
"""
Jarvis GT2 — Pre-flight Verification
=====================================
Tests credentials, API connectivity, speech sanitisation, time parsing,
intent routing, GUI push_focus types, and TTS code-filtering.

Run from the project directory:
    python preflight_test.py
"""

import os
import re
import sys
import json
import time
import unittest
import py_compile
from datetime import datetime, timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE_DIR)

PASS  = "  [OK]"
FAIL  = "  [FAIL]"
WARN  = "  [WARN]"
INFO  = "  |"

results = {"pass": 0, "fail": 0, "warn": 0}

def ok(msg):
    results["pass"] += 1
    print(f"{PASS} {msg}")

def fail(msg):
    results["fail"] += 1
    print(f"{FAIL} {msg}")

def warn(msg):
    results["warn"] += 1
    print(f"{WARN} {msg}")

def section(title):
    print(f"\n{'─'*60}")
    print(f"  {title}")
    print(f"{'─'*60}")

# ══════════════════════════════════════════════════════════════
# 0. SYNTAX CHECK
# ══════════════════════════════════════════════════════════════
section("0. SYNTAX CHECK")
try:
    py_compile.compile('jarvis_main.py', doraise=True)
    ok("jarvis_main.py - Syntax OK")
except py_compile.PyCompileError as e:
    fail(f"jarvis_main.py - Syntax Error:\n{INFO}   {e}")
    # Exit early if syntax is broken, as other tests will fail.
    sys.exit(1)
except Exception as e:
    fail(f"Could not perform syntax check: {e}")
    sys.exit(1)


# ══════════════════════════════════════════════════════════════
# 1. FILE CHECKS
# ══════════════════════════════════════════════════════════════
section("1. FILE & CREDENTIAL PRESENCE")

required_files = {
    "credentials.json":     "Google OAuth credentials",
    "token.json":           "Google auth token",
    "jarvis-high.onnx":     "Piper TTS voice model",
    "jarvis_memory.json":   "Persistent memory store",
    "jarvis_main.py":       "Main application",
    "dashboard_bridge.py":  "Dashboard WebSocket bridge",
    "memory_index.py":      "Memory index module",
}
optional_files = {
    ".env":             "Environment config",
    "yes.wav":          "Wake-word acknowledgement audio",
    "jarvis_main.py.backup": "Pre-change backup",
}

for fname, desc in required_files.items():
    if os.path.exists(fname):
        size = os.path.getsize(fname)
        ok(f"{desc} ({fname}) — {size:,} bytes")
    else:
        fail(f"{desc} ({fname}) — NOT FOUND")

for fname, desc in optional_files.items():
    if os.path.exists(fname):
        ok(f"{desc} ({fname}) — present")
    else:
        warn(f"{desc} ({fname}) — not found (optional)")


# ══════════════════════════════════════════════════════════════
# 2. ENVIRONMENT VARIABLES
# ══════════════════════════════════════════════════════════════
section("2. ENVIRONMENT VARIABLES (.env)")

try:
    from dotenv import load_dotenv
    load_dotenv()
    ok("dotenv loaded")
except ImportError:
    warn("python-dotenv not installed — reading from OS env only")

required_env = {
    "PICOVOICE_KEY":  "Wake word (Porcupine) API key",
    "OWNER_EMAIL":    "Owner email address",
}
optional_env = {
    "GOOGLE_CSE_API_KEY": "Google Custom Search key",
    "GOOGLE_CSE_CX":      "Google CSE context ID",
    "PERPLEXITY_API_KEY": "Perplexity API key",
    "BRAIN_URL":          "Ollama LLM endpoint",
    "LLM_MODEL":          "LLM model name",
    "PIPER_EXE":          "Path to piper.exe",
}

for key, desc in required_env.items():
    val = os.getenv(key, "")
    if val:
        masked = val[:8] + "…" if len(val) > 8 else val
        ok(f"{desc} ({key}) = {masked}")
    else:
        fail(f"{desc} ({key}) — NOT SET")

for key, desc in optional_env.items():
    val = os.getenv(key, "")
    if val:
        masked = val[:20] + "…" if len(val) > 20 else val
        ok(f"{desc} ({key}) = {masked}")
    else:
        warn(f"{desc} ({key}) — not set (optional)")


# ══════════════════════════════════════════════════════════════
# 3. GOOGLE TOKEN VALIDITY
# ══════════════════════════════════════════════════════════════
section("3. GOOGLE API TOKEN")

try:
    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request

    if os.path.exists("token.json"):
        SCOPES = [
            'https://www.googleapis.com/auth/gmail.send',
            'https://www.googleapis.com/auth/gmail.readonly',
            'https://www.googleapis.com/auth/calendar',
            'https://www.googleapis.com/auth/documents',
            'https://www.googleapis.com/auth/drive.file',
        ]
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
        if creds.valid:
            ok("Token is valid — no refresh needed")
        elif creds.expired and creds.refresh_token:
            creds.refresh(Request())
            ok("Token was expired — refreshed successfully")
            with open("token.json", "w") as f:
                f.write(creds.to_json())
            ok("Refreshed token saved to token.json")
        else:
            fail("Token is invalid and cannot be refreshed — re-run auth flow")

        # Quick Gmail API test
        try:
            from googleapiclient.discovery import build
            gmail = build("gmail", "v1", credentials=creds)
            profile = gmail.users().getProfile(userId="me").execute()
            ok(f"Gmail API connected — account: {profile.get('emailAddress')}")
            ok(f"  Total messages: {profile.get('messagesTotal', '?'):,}")
        except Exception as e:
            fail(f"Gmail API test failed: {e}")

        # Quick Calendar API test
        try:
            import datetime as _dt
            cal = build("calendar", "v3", credentials=creds)
            now = _dt.datetime.now(_dt.timezone.utc).isoformat()
            events = cal.events().list(
                calendarId="primary",
                timeMin=now,
                maxResults=3,
                singleEvents=True,
                orderBy="startTime"
            ).execute()
            items = events.get("items", [])
            ok(f"Calendar API connected — {len(items)} upcoming event(s) found")
            for ev in items:
                start = ev["start"].get("dateTime", ev["start"].get("date", "?"))
                ok(f"  → {ev.get('summary','Untitled')} at {start}")
        except Exception as e:
            fail(f"Calendar API test failed: {e}")
    else:
        fail("token.json not found — cannot test Google APIs")

except Exception as e:
    fail(f"Google auth setup failed: {e}")


# ══════════════════════════════════════════════════════════════
# 4. OLLAMA / LLM CONNECTIVITY
# ══════════════════════════════════════════════════════════════
section("4. OLLAMA LLM CONNECTIVITY")

try:
    import requests as _req
    brain_url = os.getenv("BRAIN_URL", "http://localhost:11434/api/generate")
    model     = os.getenv("LLM_MODEL", "llama3.1:8b")

    resp = _req.post(
        brain_url,
        json={"model": model, "prompt": "Reply with exactly: ONLINE", "stream": False},
        timeout=10
    )
    if resp.status_code == 200:
        answer = resp.json().get("response", "")
        ok(f"LLM responded: '{answer[:60].strip()}'")
    else:
        fail(f"LLM returned HTTP {resp.status_code}")
except Exception as e:
    fail(f"Ollama not reachable ({brain_url}): {e}")


# ══════════════════════════════════════════════════════════════
# 5. SPEECH SANITISATION
# ══════════════════════════════════════════════════════════════
section("5. SPEECH SANITISATION (TTS code/markdown filtering)")

def sanitize_for_speech(text):
    """Copy of jarvis_main.py sanitize_for_speech logic."""
    # Strip code fences (triple-backtick blocks) entirely
    text = re.sub(r'```[\w]*\n.*?```', 'code block omitted', text, flags=re.DOTALL)
    # Strip inline code
    text = re.sub(r'`[^`\n]+`', '', text)
    text = text.replace('°', ' degrees ')
    text = text.replace('<', '').replace('>', '')
    text = text.replace('@', ' at ')
    text = text.replace('*', '').replace('#', '').replace('_', '')
    text = text.replace('`', '').replace('~', '').replace('|', '')
    text = text.replace('[', '').replace(']', '')
    text = text.replace('{', '').replace('}', '')
    text = ' '.join(text.split())
    return text

test_cases = [
    # (label, input, what_must_NOT_be_in_output)
    ("Markdown bold",
     "Your **meeting** is at 2pm",
     ["**"]),
    ("Inline code backtick",
     "Run `pip install requests` to fix it",
     ["`"]),
    ("Code fence",
     "```python\ndef hello():\n    print('Hello')\n```",
     ["```", "def ", "print("]),
    ("Email @ symbol",
     "Email from user@example.com regarding the project",
     ["@"]),
    ("Hash / markdown heading",
     "## Summary\n### Key Points",
     ["##", "###"]),
    ("Degree symbol",
     "Temperature is 22°C today",
     ["°"]),
    ("Angle brackets",
     "Response from <server>: <OK>",
     ["<", ">"]),
    ("Curly braces",
     "JSON payload: {\"key\": \"value\"}",
     ["{", "}"]),
    ("Multiple spaces",
     "Hello   there   Sir",
     ["   "]),
    ("Underscore",
     "File is jarvis_main_backup.py",
     ["_"]),
]

for label, inp, must_not_contain in test_cases:
    result = sanitize_for_speech(inp)
    bad = [tok for tok in must_not_contain if tok in result]
    if bad:
        fail(f"{label}: output still contains {bad}\n{INFO}   Input:  {inp[:60]}\n{INFO}   Output: {result[:60]}")
    else:
        ok(f"{label}: clean → '{result[:55]}'")

# Verify code blocks are stripped (the real concern)
code_input = (
    "Here is the function:\n"
    "```python\n"
    "def process_conversation(self, raw_text):\n"
    "    text_lower = raw_text.lower()\n"
    "    for i in range(10):\n"
    "        print(f'step {i}')\n"
    "```\n"
    "That is all."
)
cleaned = sanitize_for_speech(code_input)
if "def " not in cleaned and "for i in" not in cleaned:
    ok("Code block content: function/loop syntax removed from speech output")
else:
    # Note: sanitize_for_speech only strips symbols, not keywords
    # The LLM should not return raw code, but we flag this
    warn("sanitize_for_speech strips symbols only — LLM must not return raw code blocks")
    print(f"     Cleaned: {cleaned[:80]}")


# ══════════════════════════════════════════════════════════════
# 6. RELATIVE TIME PARSER
# ══════════════════════════════════════════════════════════════
section("6. RELATIVE TIME PARSER")

def parse_relative_datetime(time_expr):
    """Copy of jarvis_main.py parse_relative_datetime."""
    now = datetime.now()
    text = time_expr.lower().strip()

    m = re.search(r'in\s+(\d+)\s+(minute|hour|day)s?', text)
    if m:
        amount = int(m.group(1))
        unit = m.group(2)
        delta = {'minute': timedelta(minutes=amount),
                 'hour':   timedelta(hours=amount),
                 'day':    timedelta(days=amount)}[unit]
        start_dt = now + delta
        return start_dt, start_dt + timedelta(hours=1)

    day_names = ['monday','tuesday','wednesday','thursday',
                 'friday','saturday','sunday']
    for i, day in enumerate(day_names):
        if day in text:
            days_ahead = (i - now.weekday()) % 7 or 7
            base = (now + timedelta(days=days_ahead)).replace(second=0, microsecond=0)
            hour = 9
            if 'afternoon' in text: hour = 14
            elif 'evening' in text: hour = 19
            start_dt = base.replace(hour=hour, minute=0)
            return start_dt, start_dt + timedelta(hours=1)

    if 'tomorrow' in text:
        base = (now + timedelta(days=1)).replace(second=0, microsecond=0)
        hour = 9
        if 'afternoon' in text: hour = 14
        elif 'evening' in text or 'night' in text: hour = 19
        start_dt = base.replace(hour=hour, minute=0)
        return start_dt, start_dt + timedelta(hours=1)

    if 'this evening' in text or 'tonight' in text:
        start_dt = now.replace(hour=19, minute=0, second=0, microsecond=0)
        if start_dt <= now: start_dt += timedelta(days=1)
        return start_dt, start_dt + timedelta(hours=1)

    if 'after lunch' in text:
        start_dt = now.replace(hour=13, minute=30, second=0, microsecond=0)
        if start_dt <= now: start_dt += timedelta(days=1)
        return start_dt, start_dt + timedelta(hours=1)

    if 'next week' in text:
        start_dt = (now + timedelta(days=7)).replace(hour=9, minute=0, second=0, microsecond=0)
        return start_dt, start_dt + timedelta(hours=1)

    if 'later' in text or 'this afternoon' in text:
        if now.hour < 14:
            start_dt = now.replace(hour=14, minute=0, second=0, microsecond=0)
        else:
            start_dt = (now + timedelta(hours=2)).replace(second=0, microsecond=0)
        return start_dt, start_dt + timedelta(hours=1)

    return None, None

time_cases = [
    ("in 2 hours",               lambda s: s and (s - datetime.now()).seconds // 3600 == 2),
    ("in 30 minutes",            lambda s: s and 1700 < (s - datetime.now()).seconds < 1900),
    ("tomorrow",                 lambda s: s and s.day == (datetime.now() + timedelta(days=1)).day and s.hour == 9),
    ("tomorrow afternoon",       lambda s: s and s.hour == 14),
    ("tomorrow evening",         lambda s: s and s.hour == 19),
    ("this evening",             lambda s: s and s.hour == 19),
    ("after lunch",              lambda s: s and s.hour == 13 and s.minute == 30),
    ("next week",                lambda s: s and s > datetime.now() + timedelta(days=6)),
    ("thursday",                 lambda s: s and s.weekday() == 3),
    ("friday afternoon",         lambda s: s and s.weekday() == 4 and s.hour == 14),
    ("book a call tomorrow",     lambda s: s and s.day == (datetime.now() + timedelta(days=1)).day),
    ("no time here",             lambda s: s is None),
]

for expr, validator in time_cases:
    s, e = parse_relative_datetime(expr)
    if validator(s):
        ts = s.strftime("%a %d %b %H:%M") if s else "None"
        ok(f"'{expr}' → {ts}")
    else:
        ts = s.strftime("%a %d %b %H:%M") if s else "None"
        fail(f"'{expr}' → {ts} (unexpected result)")


# ══════════════════════════════════════════════════════════════
# 7. INTENT ROUTING SIMULATION
# ══════════════════════════════════════════════════════════════
section("7. INTENT ROUTING SIMULATION")

# This simulation must be kept in sync with jarvis_main.py's INTENTS dict and routing logic
try:
    # Dynamically import to ensure we're testing the latest version
    from jarvis_main import INTENTS as SIMULATED_INTENTS
    ok("Loaded INTENTS from jarvis_main.py")
except (ImportError, SyntaxError) as e:
    fail(f"Could not import INTENTS from jarvis_main.py: {e}")
    SIMULATED_INTENTS = {}

def simulate_route(raw_text):
    """Simulate the score-based intent router from jarvis_main.py."""
    if not SIMULATED_INTENTS:
        return "FAIL_TO_LOAD"

    text_lower = raw_text.lower()
    scores = {}

    for intent, config in SIMULATED_INTENTS.items():
        score = 0
        if 'regex' in config and re.search(config['regex'], text_lower):
            score += 10
        if 'keywords' in config:
            score += sum(1 for kw in config['keywords'] if kw in text_lower)
        if 'required' in config:
            if any(req in text_lower for req in config['required']):
                score += 5
            elif score > 0:
                score = 0
        if 'blockers' in config and any(blk in text_lower for blk in config['blockers']):
            score = 0
        if score > 0:
            scores[intent] = score

    if not scores:
        return "LLM_BRAIN"

    sorted_intents = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    best_intent, best_score = sorted_intents[0]

    if len(sorted_intents) > 1:
        second_best_intent, second_best_score = sorted_intents[1]
        if best_score > 0 and (best_score / second_best_score) < 1.5:
            return f"AMBIGUOUS ({best_intent} vs {second_best_intent})"

    CONFIDENCE_THRESHOLD = 1
    if best_score <= CONFIDENCE_THRESHOLD:
        return "LLM_BRAIN"

    return best_intent

routing_cases = [
    # --- CALENDAR_READ ---
    ("What's my day look like?", "CALENDAR_READ", "Calendar read: natural"),
    ("What do I have on today?", "CALENDAR_READ", "Calendar read: 'what do I have'"),
    ("What have I got on?", "CALENDAR_READ", "Calendar read: 'what have I got'"),
    ("Show me my calendar", "CALENDAR_READ", "Calendar read: direct"),
    ("What's on my schedule for tomorrow?", "CALENDAR_READ", "Calendar read: with time"),
    ("Do I have any upcoming events?", "CALENDAR_READ", "Calendar read: 'upcoming'"),
    ("Check my diary", "CALENDAR_READ", "Calendar read: 'diary'"),

    # --- CALENDAR_ACTION ---
    ("Book a call with David tomorrow afternoon", "CALENDAR_ACTION", "Calendar create: 'book'"),
    ("Cancel my 2pm meeting", "CALENDAR_ACTION", "Calendar cancel: direct"),
    ("Schedule a meeting with the team on Friday", "CALENDAR_ACTION", "Calendar create: 'schedule a meeting'"),
    ("Move the first one to Thursday", "CALENDAR_ACTION", "Calendar move: contextual"),
    ("Add an event for lunch", "CALENDAR_ACTION", "Calendar create: 'add an event'"),
    ("Reschedule my call for 3pm", "CALENDAR_ACTION", "Calendar reschedule"),
    ("Create a new event called 'Doctor Appointment'", "CALENDAR_ACTION", "Calendar create: 'create an event'"),

    # --- EMAIL_SUMMARY ---
    ("Summarize my emails", "EMAIL_SUMMARY", "Email summary: direct"),
    ("Read my emails", "EMAIL_SUMMARY", "Email summary: 'read'"),
    ("What's new in my mail?", "EMAIL_SUMMARY", "Email summary: natural"),
    ("Show me a summary of my emails", "EMAIL_SUMMARY", "Email summary: verbose"),
    ("Can you check my mail?", "EMAIL_SUMMARY", "Email summary: 'check mail'"),

    # --- EMAIL_SEARCH ---
    ("Find emails from Sarah", "EMAIL_SEARCH", "Email search: by name"),
    ("Search for an email from john.doe@example.com", "EMAIL_SEARCH", "Email search: by email"),
    ("Look for messages about the 'Dogzilla' project", "EMAIL_SEARCH", "Email search: by subject"),
    ("Find me the mail from David about the invoice", "EMAIL_SEARCH", "Email search: name and subject"),

    # --- EMAIL_REPLY ---
    ("Reply to the last email saying I'll call you back", "EMAIL_REPLY", "Email reply: with message"),
    ("Answer the last message and say I agree", "EMAIL_REPLY", "Email reply: 'answer'"),
    ("Respond to the email with 'Thanks'", "EMAIL_REPLY", "Email reply: 'respond'"),

    # --- EMAIL_MANAGEMENT ---
    ("Archive that email", "EMAIL_MANAGEMENT", "Email management: archive"),
    ("Mark that handled", "EMAIL_MANAGEMENT", "Email management: mark handled"),
    ("Trash that email", "EMAIL_MANAGEMENT", "Email management: trash"),
    ("Delete the last email", "EMAIL_MANAGEMENT", "Email management: delete"),
    ("Bin it", "EMAIL_MANAGEMENT", "Email management: 'bin it'"),

    # --- TASK ---
    ("Remind me to order dog food", "TASK", "Task create: 'remind me'"),
    ("Add to my list: call the dentist", "TASK", "Task create: 'add to my list'"),
    ("Note to self, buy milk", "TASK", "Task create: 'note to self'"),
    ("What's on my list?", "TASK", "Task list: direct"),
    ("Show me my tasks", "TASK", "Task list: 'show tasks'"),
    ("What do I need to do?", "TASK", "Task list: natural"),
    ("Mark the first task as done", "TASK", "Task complete: by index"),
    ("I've finished the report task", "TASK", "Task complete: by keyword"),
    ("Complete task number two", "TASK", "Task complete: by number"),

    # --- MEMORY_RECALL ---
    ("Did I ever order that dog food?", "MEMORY_RECALL", "Memory recall: 'did I ever'"),
    ("Have I called David back yet?", "MEMORY_RECALL", "Memory recall: 'have I'"),
    ("Did we ever discuss the budget?", "MEMORY_RECALL", "Memory recall: 'did we'"),

    # --- LEARN_FACT ---
    ("Remember that my car is a BMW", "LEARN_FACT", "Learn fact: 'remember that'"),
    ("Note that I moved to a new city", "LEARN_FACT", "Learn fact: 'note that'"),
    ("Update: my new phone number is 123", "LEARN_FACT", "Learn fact: 'update'"),
    ("Correction: I work at Google now", "LEARN_FACT", "Learn fact: 'correction'"),
    ("Forget that I had a Ford", "LEARN_FACT", "Forget fact: 'forget that'"),
    ("That's wrong, I don't live there anymore", "LEARN_FACT", "Forget fact: 'that's wrong'"),

    # --- WEB_SEARCH ---
    ("What is Python?", "WEB_SEARCH", "Web search: 'what is'"),
    ("Who is the current prime minister?", "WEB_SEARCH", "Web search: 'who is'"),
    ("Search for best practices in REST APIs", "WEB_SEARCH", "Web search: 'search for'"),
    ("Google the price of gold", "WEB_SEARCH", "Web search: 'google'"),
    ("Find out the capital of Australia", "WEB_SEARCH", "Web search: 'find out'"),

    # --- CODE_OPTIMIZATION ---
    ("Analyze the main file", "CODE_OPTIMIZATION", "Code optimization: 'analyze file'"),
    ("Optimize this python script", "CODE_OPTIMIZATION", "Code optimization: 'optimize script'"),
    ("Can you analyze my code?", "CODE_OPTIMIZATION", "Code optimization: 'analyze code'"),

    # --- REPORT_RETRIEVAL ---
    ("Show me the latest optimization report", "REPORT_RETRIEVAL", "Report retrieval: 'latest report'"),
    ("Open the last document you created", "REPORT_RETRIEVAL", "Report retrieval: 'last document'"),
    ("What was in the recent summary?", "REPORT_RETRIEVAL", "Report retrieval: 'recent summary'"),

    # --- FILE_COMPARISON ---
    ("Compare the main file and the backup file", "FILE_COMPARISON", "File comparison: direct"),
    ("What's the comparison between the two scripts?", "FILE_COMPARISON", "File comparison: natural"),

    # --- MISC / PROJECT SPECIFIC ---
    ("What's the weather like today?", "WEATHER", "Misc: Weather query"),
    ("Who are you?", "SELF_KNOWLEDGE", "Misc: Self-knowledge query"),
    ("What do you know about me?", "SELF_KNOWLEDGE", "Misc: Self-knowledge 'about me'"),
    ("Tell me about project dogzilla", "PROJECT_DOGZILLA", "Misc: Project Dogzilla"),

    # --- AMBIGUITY & EDGE CASES ---
    ("Search my calendar for meetings", "AMBIGUOUS (CALENDAR_READ vs WEB_SEARCH)", "Ambiguity: search + calendar"),
    ("Remind me to search for that email", "AMBIGUOUS (TASK vs EMAIL_SEARCH)", "Ambiguity: remind + search email"),
    ("Book a flight", "LLM_BRAIN", "Edge case: 'book' without calendar context"),
    ("Add a calendar event", "CALENDAR_ACTION", "Edge case: 'add' with calendar context"),
    ("Add a note to my email", "LLM_BRAIN", "Edge case: Vague, no clear tool"),
    ("Read the book", "LLM_BRAIN", "Edge case: 'read' without email/report context"),
    ("I need to book my calendar", "CALENDAR_ACTION", "Edge case: 'book' with calendar context"),
    ("I need to read my book", "LLM_BRAIN", "Edge case: 'read' without tool context"),
    ("Search", "WEB_SEARCH", "Edge case: single keyword 'search'"),
    ("Email", "EMAIL_SUMMARY", "Edge case: single keyword 'email'"),
    ("Calendar", "CALENDAR_READ", "Edge case: single keyword 'calendar'"),
    ("Task", "TASK", "Edge case: single keyword 'task'"),
    ("Analyze", "LLM_BRAIN", "Edge case: 'analyze' without file/code"),
    ("Analyze the situation", "LLM_BRAIN", "Edge case: 'analyze' without file/code"),
    ("Optimize my day", "LLM_BRAIN", "Edge case: 'optimize' without file/code"),
    ("Show me the file", "LLM_BRAIN", "Edge case: 'show file' without 'last'/'recent'"),
    ("Read the document", "LLM_BRAIN", "Edge case: 'read document' without 'last'/'recent'"),
    ("Summarize", "LLM_BRAIN", "Edge case: 'summarize' without context"),
    ("Find", "WEB_SEARCH", "Edge case: 'find' without context"),
    ("Reply", "LLM_BRAIN", "Edge case: 'reply' without context"),
    ("Move", "LLM_BRAIN", "Edge case: 'move' without context"),
    ("Cancel", "LLM_BRAIN", "Edge case: 'cancel' without context"),

    # --- LLM_BRAIN FALLBACKS ---
    ("Good morning", "LLM_BRAIN", "General conversation: Greeting"),
    ("Tell me a joke", "LLM_BRAIN", "General conversation: Request"),
    ("How are you feeling today Jarvis?", "LLM_BRAIN", "General conversation: Question"),
    ("What's the capital of France?", "WEB_SEARCH", "Factual question (should route to search)"),
    ("Explain quantum physics", "WEB_SEARCH", "Factual question (should route to search)"),
    ("Thank you", "LLM_BRAIN", "General conversation: Politeness"),
    ("That's all for now", "LLM_BRAIN", "General conversation: Closing"),
    ("Who won the world cup in 1998?", "WEB_SEARCH", "Factual question (should route to search)"),
    ("Set a timer for 5 minutes", "LLM_BRAIN", "Unsupported tool: timer"),
    ("Play some music", "LLM_BRAIN", "Unsupported tool: music"),
    ("Turn on the lights", "LLM_BRAIN", "Unsupported tool: smarthome"),
    ("What's my IP address?", "WEB_SEARCH", "Factual question (should route to search)"),
    ("Can you write some code for me?", "LLM_BRAIN", "General request for LLM"),
    ("What do you think about AI?", "LLM_BRAIN", "General opinion question"),
    ("How does your intent router work?", "LLM_BRAIN", "Metacognitive question"),
]

for query, expected, desc in routing_cases:
    got = simulate_route(query)
    if got == expected:
        ok(f"{desc}\n{INFO}   '{query[:55]}' → {got}")
    else:
        fail(f"{desc}\n{INFO}   '{query[:55]}'\n{INFO}   Expected: {expected}  Got: {got}")


# ══════════════════════════════════════════════════════════════
# 8. CONTEXT-AWARE FOLLOW-UP ROUTING
# ══════════════════════════════════════════════════════════════
section("8. CONTEXT-AWARE FOLLOW-UP ROUTING")

def simulate_context_route(raw_text, last_intent, has_calendar_events=True):
    """Simulate _route_by_context without actual handler calls."""
    text_lower = raw_text.lower()
    if not last_intent:
        return "NO_CONTEXT"

    if last_intent == "email":
        if (any(w in text_lower for w in ["reply", "respond", "answer"])
                and "email" not in text_lower and "mail" not in text_lower):
            return "EMAIL_REPLY_CONTEXTUAL"
        if any(w in text_lower for w in [
                "archive", "handled", "bin", "trash", "delete it", "delete that"]):
            return "EMAIL_MANAGEMENT_CONTEXTUAL"

    if last_intent == "calendar":
        if (any(w in text_lower for w in [
                "move", "reschedule", "cancel", "delete", "first", "second", "third"])
                and has_calendar_events):
            return "CALENDAR_ACTION_CONTEXTUAL"

    if last_intent == "task":
        if any(w in text_lower for w in [
                "done", "complete", "finished", "mark", "add another", "remind me"]):
            return "TASK_CONTEXTUAL"

    return "NOT_ROUTED"

context_cases = [
    ("reply to that",   "email",    False, "EMAIL_REPLY_CONTEXTUAL",
     "After email context: 'reply to that' without 'email' keyword"),
    ("respond to it",   "email",    False, "EMAIL_REPLY_CONTEXTUAL",
     "After email context: 'respond to it'"),
    ("archive it",      "email",    False, "EMAIL_MANAGEMENT_CONTEXTUAL",
     "After email context: 'archive it'"),
    ("bin that",        "email",    False, "EMAIL_MANAGEMENT_CONTEXTUAL",
     "After email context: 'bin that'"),
    ("move the first one to Thursday", "calendar", True, "CALENDAR_ACTION_CONTEXTUAL",
     "After calendar: 'move the first one'"),
    ("cancel it",       "calendar", True, "CALENDAR_ACTION_CONTEXTUAL",
     "After calendar: 'cancel it'"),
    ("mark the first one done", "task", False, "TASK_CONTEXTUAL",
     "After task context: 'mark the first one done'"),
    ("remind me again",  "task",    False, "TASK_CONTEXTUAL",
     "After task context: 'remind me again'"),
    ("tell me a joke",   "email",   False, "NOT_ROUTED",
     "Unrelated follow-up after email: should fall through to LLM"),
]

for query, last_intent, has_events, expected, desc in context_cases:
    got = simulate_context_route(query, last_intent, has_events)
    if got == expected:
        ok(f"{desc}")
    else:
        fail(f"{desc}\n{INFO}   '{query}' (last_intent={last_intent})\n{INFO}   Expected: {expected}  Got: {got}")


# ══════════════════════════════════════════════════════════════
# 9. GUI push_focus TYPE VALIDATION
# ══════════════════════════════════════════════════════════════
section("9. GUI push_focus CONTENT TYPE VALIDATION")

VALID_FOCUS_TYPES = {"docs", "code", "email"}

with open("jarvis_main.py", "r", encoding="utf-8") as f:
    source = f.read()

# Find all push_focus calls
push_focus_calls = re.findall(
    r'push_focus\s*\(\s*(?:content_type\s*=\s*)?["\']([^"\']+)["\']', source)

invalid = [t for t in push_focus_calls if t not in VALID_FOCUS_TYPES]

if invalid:
    fail(f"Invalid push_focus content_type(s) found: {invalid}")
else:
    ok(f"All {len(push_focus_calls)} push_focus calls use valid types "
       f"({sorted(VALID_FOCUS_TYPES)})")

# Show breakdown
from collections import Counter
counts = Counter(push_focus_calls)
for ctype, n in sorted(counts.items()):
    ok(f"  type='{ctype}' used {n} time(s)")


# ══════════════════════════════════════════════════════════════
# 10. MEMORY / TASK SYSTEM
# ══════════════════════════════════════════════════════════════
section("10. MEMORY & TASK SYSTEM")

try:
    with open("jarvis_memory.json", "r", encoding="utf-8") as f:
        mem = json.load(f)

    facts = mem.get("facts", [])
    projects = mem.get("projects", {})
    actions = mem.get("vault_actions", [])
    tasks = mem.get("tasks", [])
    profile = mem.get("master_profile", {})

    ok(f"Memory loaded: {len(facts)} facts, {len(projects)} projects, "
       f"{len(actions)} past actions, {len(tasks)} tasks")

    if profile.get("name"):
        ok(f"Master profile: {profile['name']} — health data present: "
           f"{bool(profile.get('health_profile'))}")
    else:
        warn("No master profile name found in memory")

    # Validate task structure
    bad_tasks = [t for t in tasks if not all(
        k in t for k in ["id", "description", "done"])]
    if bad_tasks:
        warn(f"{len(bad_tasks)} task(s) missing required fields")
    elif tasks:
        active = [t for t in tasks if not t.get("done")]
        done   = [t for t in tasks if t.get("done")]
        ok(f"Task system: {len(active)} active, {len(done)} completed")
    else:
        ok("Task list is empty (ready for use)")

except Exception as e:
    fail(f"Could not load jarvis_memory.json: {e}")


# ══════════════════════════════════════════════════════════════
# 11. PENDING CONFIRMATION STATE MACHINE
# ══════════════════════════════════════════════════════════════
section("11. PENDING CONFIRMATION LOGIC")

def simulate_confirmation(pending_reply, user_text):
    """Simulate check_pending_confirmation without full class."""
    text_lower = user_text.lower().strip()
    confirm = ['yes','yeah','yep','send it','send that','go ahead',
               'do it','ok','okay','confirm','correct','sure','please']
    deny    = ['no','nope','cancel',"don't",'dont','stop','abort',
               'wait','hold on','actually']

    if pending_reply:
        if any(w in text_lower for w in confirm):
            return "SEND_EMAIL"
        if any(w in text_lower for w in deny):
            return "CANCEL_EMAIL"
        return "REMIND_PENDING"
    return "PASSTHROUGH"

conf_cases = [
    (True,  "yes",           "SEND_EMAIL",     "Confirm with 'yes'"),
    (True,  "go ahead",      "SEND_EMAIL",     "Confirm with 'go ahead'"),
    (True,  "ok send it",    "SEND_EMAIL",     "Confirm with 'ok send it'"),
    (True,  "no don't send", "CANCEL_EMAIL",   "Cancel with 'no'"),
    (True,  "cancel that",   "CANCEL_EMAIL",   "Cancel with 'cancel'"),
    (True,  "actually wait", "CANCEL_EMAIL",   "Cancel with 'actually wait'"),
    (True,  "what time is it","REMIND_PENDING","Unrelated → remind about pending"),
    (False, "yes",           "PASSTHROUGH",    "No pending reply → passthrough"),
]

for has_pending, text, expected, desc in conf_cases:
    got = simulate_confirmation(has_pending, text)
    if got == expected:
        ok(f"{desc}: '{text}' → {got}")
    else:
        fail(f"{desc}: '{text}' → expected {expected}, got {got}")


# ══════════════════════════════════════════════════════════════
# 12. NOTIFICATION QUEUE SIMULATION
# ══════════════════════════════════════════════════════════════
section("12. NOTIFICATION QUEUE SIMULATION")

def simulate_notification_processing(queue, context="idle"):
    """Simulate the logic of process_notification_queue."""
    if not queue:
        return None

    by_source = collections.defaultdict(list)
    for n in queue:
        by_source[n.get('source', 'Unknown')].append(n)

    parts = []
    for src, items in sorted(by_source.items()): # sorted for deterministic order
        if len(items) == 1:
            parts.append(items[0]['message'])
        else:
            plural_src = src + 's' if not src.endswith('s') else src
            parts.append(f"you have {len(items)} {plural_src} updates")

    if not parts:
        return None

    summary = ("Also, " if context == "busy" else "Sir, ") + ", and ".join(parts) + "."
    return summary

# Test cases based on the *fixed* logic
notification_cases = [
    (
        "Single email (idle)", "idle",
        [{"source": "email", "message": "you have a new email from John Doe regarding Project Updates"}],
        "Sir, you have a new email from John Doe regarding Project Updates."
    ),
    (
        "Multiple emails (idle)", "idle",
        [{"source": "email", "message": "email 1"}, {"source": "email", "message": "email 2"}],
        "Sir, you have 2 emails updates."
    ),
    (
        "Multiple sources (busy)", "busy",
        [
            {"source": "email", "message": "email 1"},
            {"source": "Reminder", "message": "Reminder: take out bins"},
            {"source": "email", "message": "email 2"},
        ],
        "Also, Reminder: take out bins, and you have 2 emails updates."
    ),
    (
        "Empty queue", "idle", [], None
    ),
    (
        "Single reminder (busy)", "busy",
        [{"source": "Reminder", "message": "Sir, reminder: Check server status"}],
        "Also, Sir, reminder: Check server status."
    ),
]

for desc, context, queue, expected in notification_cases:
    got = simulate_notification_processing(queue, context)
    if got == expected:
        ok(f"{desc}")
    else:
        fail(f"{desc}\n{INFO}   Expected: {expected}\n{INFO}   Got:      {got}")


# ══════════════════════════════════════════════════════════════
# 13. VISUAL ADDRESSING & RECALL SYSTEM
# ══════════════════════════════════════════════════════════════
section("13. VISUAL ADDRESSING & RECALL SYSTEM (Short-Key Commands)")

try:
    # Dynamically import to test the latest versions
    from jarvis_main import JarvisGT2
    from core.context_manager import SessionContext
    from unittest.mock import MagicMock, patch

    class TestRecallSystem(unittest.TestCase):
        def setUp(self):
            """Set up a mock Jarvis instance with a real SessionContext."""
            # We patch the __init__ to avoid hardware/network dependencies
            with patch('jarvis_main.JarvisGT2.__init__', return_value=None):
                self.jarvis = JarvisGT2()
                self.jarvis.session_context = SessionContext()
                
                # Mock methods that have external side effects
                self.jarvis.log = MagicMock()
                self.jarvis.speak_with_piper = MagicMock()
                self.jarvis.handle_deep_dig = MagicMock()
                self.jarvis.dashboard = MagicMock()
                self.jarvis.dashboard.push_focus = MagicMock()

        def test_email_follow_up_display(self):
            """Test Case: 'show e1' should display the email."""
            # 1. Simulate an email search populating the context
            self.jarvis.session_context.add_item(
                full_key="20260211-e1",
                label="Kent Robotics",
                item_type='e',
                metadata={'id': 'email123', 'sender': 'kent@robotics.com'}
            )
            
            # 2. Simulate user request
            handled = self.jarvis._handle_contextual_command("show e1")
            
            # 3. Verify
            self.assertTrue(handled, "Command 'show e1' was not handled")
            self.jarvis.speak_with_piper.assert_called_with("Bringing up email e1 from Kent Robotics.")
            self.jarvis.dashboard.push_focus.assert_called_once()
            ok("Contextual command 'show e1' correctly triggered dashboard focus")

        @patch('webbrowser.open')
        def test_web_result_follow_up_open(self, mock_webbrowser_open):
            """Test Case: 'open wr1' should open a URL."""
            # 1. Simulate a web search
            self.jarvis.session_context.add_item(
                full_key="20260211-wr1",
                label="AI News",
                item_type='w',
                metadata={'url': 'https://example.com/ai-news'}
            )
            
            # 2. Simulate user request
            handled = self.jarvis._handle_contextual_command("open wr1")
            
            # 3. Verify
            self.assertTrue(handled, "Command 'open wr1' was not handled")
            mock_webbrowser_open.assert_called_with('https://example.com/ai-news')
            ok("Contextual command 'open wr1' correctly triggered webbrowser")

        def test_deep_dig_follow_up(self):
            """Test Case: 'dig deeper into wr2' should trigger the deep dig handler."""
            # 1. Simulate a web search
            item_to_dig = {
                "full_key": "20260211-wr2",
                "label": "Python Docs",
                "type": 'w',
                "metadata": {'url': 'https://python.org'}
            }
            self.jarvis.session_context.add_item(**item_to_dig)
            
            # 2. Simulate user request
            handled = self.jarvis._handle_contextual_command("dig deeper into wr2")
            
            # 3. Verify
            self.assertTrue(handled, "Command 'dig deeper into wr2' was not handled")
            self.jarvis.handle_deep_dig.assert_called_with(item_to_dig)
            ok("Contextual command 'dig deeper into wr2' correctly triggered deep dig handler")

        @patch('webbrowser.open')
        def test_multi_stage_flow_web_to_deep_dig_to_display(self, mock_webbrowser_open):
            """
            Test Case: Simulate a multi-stage flow:
            1. Web search populates wr1.
            2. "dig deeper into wr1" triggers deep dig, which creates d1.
            3. "show d1" displays the document.
            """
            # 1. Simulate initial web search results
            mock_web_results = [
                {'title': 'AI News Today', 'snippet': 'Latest AI breakthroughs.', 'link': 'https://example.com/ai-news'},
                {'title': 'Python Updates', 'snippet': 'New features in Python.', 'link': 'https://example.com/python-updates'}
            ]
            with patch('jarvis_main.JarvisGT2.google_search', return_value=mock_web_results):
                # We need a real ConversationalLedger and ShortKeyGenerator for this
                self.jarvis.short_key_generator = MagicMock(spec=self.jarvis.short_key_generator)
                self.jarvis.conversational_ledger = MagicMock(spec=self.jarvis.conversational_ledger)
                
                # Mock generate to return predictable keys
                self.jarvis.short_key_generator.generate.side_effect = ["20260211-w1", "20260211-w2", "20260211-d1"]
                
                # Mock add_entry to return predictable ledger entries
                self.jarvis.conversational_ledger.add_entry.side_effect = [
                    {'metadata': {'short_key': "20260211-w1"}},
                    {'metadata': {'short_key': "20260211-w2"}},
                    {'metadata': {'short_key': "20260211-d1", 'source_url': 'https://example.com/ai-news', 'summary': 'Mocked deep dig summary'}}
                ]

                self.jarvis.handle_web_search("search for AI news")
            
            self.assertIsNotNone(self.jarvis.session_context.get_item('wr1'), "wr1 not found in session context after web search")
            self.jarvis.dashboard.update_ticker.assert_called_once()
            ok("Multi-stage: Web search populated session context and ticker")

            # 2. Simulate "dig deeper into wr1"
            # Manually add the expected 'd1' item to session_context as handle_deep_dig would do
            self.jarvis.session_context.add_item(
                full_key="20260211-d1",
                label="Analysis: AI News Today",
                item_type='d',
                metadata={'source_url': 'https://example.com/ai-news', 'summary': 'Mocked deep dig summary'}
            )
            handled_dig = self.jarvis._handle_contextual_command("dig deeper into wr1")
            self.assertTrue(handled_dig, "Command 'dig deeper into wr1' was not handled")
            self.jarvis.handle_deep_dig.assert_called_once()
            ok("Multi-stage: 'dig deeper into wr1' triggered deep dig handler")

            # 3. Simulate "show d1"
            handled_show_d1 = self.jarvis._handle_contextual_command("show d1")
            self.assertTrue(handled_show_d1, "Command 'show d1' was not handled")
            self.jarvis.speak_with_piper.assert_called_with("Displaying the analysis for d1.")
            self.jarvis.dashboard.push_focus.assert_called_with(
                "docs", "Analysis: AI News Today", "Source: https://example.com/ai-news\n\n---\n\nMocked deep dig summary"
            )
            ok("Multi-stage: 'show d1' correctly displayed the document")

    # Run the tests
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(TestRecallSystem))
    runner = unittest.TextTestRunner(stream=sys.stdout, verbosity=0)
    # Suppress runner's output, we use our own ok/fail
    result = runner.run(suite)
    if result.failures or result.errors:
        fail(f"Recall System Tests failed: {len(result.failures)} failures, {len(result.errors)} errors")

except (ImportError, Exception) as e:
    fail(f"Could not run Recall System tests: {e}")

# ══════════════════════════════════════════════════════════════
# SUMMARY
# ══════════════════════════════════════════════════════════════
section("RESULTS SUMMARY")

total = results["pass"] + results["fail"] + results["warn"]
print(f"\n  Passed : {results['pass']:>3}")
print(f"  Warned : {results['warn']:>3}  (non-blocking)")
print(f"  Failed : {results['fail']:>3}")
print(f"  Total  : {total:>3}")

if results["fail"] == 0:
    print("\n  ✓ ALL CHECKS PASSED — safe to start Jarvis\n")
elif results["fail"] <= 3:
    print("\n  ⚠  MINOR FAILURES — check the items above before starting\n")
else:
    print("\n  ✗ SIGNIFICANT FAILURES — resolve before starting Jarvis\n")
