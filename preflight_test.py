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

def simulate_route(raw_text):
    """Simulate process_conversation intent routing without executing handlers."""
    text_lower = raw_text.lower()

    # Ordered exactly as in process_conversation
    if ("who are you" in text_lower or "what do you know about me" in text_lower
            or "tell me about yourself" in text_lower):
        return "SELF_KNOWLEDGE"

    if "dogzilla" in text_lower:
        return "PROJECT_DOGZILLA"

    if "weather" in text_lower:
        return "WEATHER"

    if (any(w in text_lower for w in [
            "remind me", "reminder", "add to my list", "don't forget",
            "note to self", "remember to"])
        or any(w in text_lower for w in [
            "what's on my list", "my tasks", "pending tasks",
            "show tasks", "list tasks",
            "what do i need to do", "what have i got"])):
        return "TASK"

    if re.search(r'\b(?:did|have)\s+(?:i|you|we)\s+(?:ever\s+)?\w', text_lower):
        return "TASK_RECALL"

    if (any(w in text_lower for w in [
            "calendar", "what's my day", "my day", "diary",
            "upcoming", "today's events", "schedule today",
            "what do i have"])
        and not any(w in text_lower for w in [
            "book", "schedule a", "add to calendar",
            "create event", "move", "reschedule", "cancel"])):
        return "CALENDAR_READ"

    if (any(w in text_lower for w in [
            "book", "cancel", "reschedule",
            "move the", "move my", "create an event", "add an event"])
        or ("schedule" in text_lower and any(
            w in text_lower for w in [
                "a call", "a meeting", "an appointment",
                "with ", "tomorrow", "monday", "tuesday",
                "wednesday", "thursday", "friday"]))):
        return "CALENDAR_ACTION"

    if (("open" in text_lower or "show" in text_lower
         or "read" in text_lower or "summarize" in text_lower
         or "summary" in text_lower)
        and ("last" in text_lower or "latest" in text_lower or "recent" in text_lower)
        and ("report" in text_lower or "optimization" in text_lower
             or "document" in text_lower)):
        return "REPORT_RETRIEVAL"

    if (("check" in text_lower and "file" in text_lower
         and ("write" in text_lower or "doc" in text_lower))
        or ("analyze" in text_lower and "file" in text_lower)
        or ("optimize" in text_lower and "file" in text_lower)):
        return "CODE_OPTIMIZATION"

    if (("summarize" in text_lower or "summary" in text_lower
         or "read" in text_lower or "show" in text_lower)
        and ("email" in text_lower or "emails" in text_lower or "mail" in text_lower)):
        return "EMAIL_SUMMARY"

    if (("search" in text_lower or "find" in text_lower or "look for" in text_lower)
        and ("email" in text_lower or "mail from" in text_lower
             or "message from" in text_lower)):
        return "EMAIL_SEARCH"

    if (("reply" in text_lower or "respond" in text_lower or "answer" in text_lower)
        and ("email" in text_lower or "mail" in text_lower
             or ("last" in text_lower and "message" in text_lower))):
        return "EMAIL_REPLY"

    if (any(w in text_lower for w in [
            "archive", "bin it", "bin that", "trash that",
            "trash it", "delete that email", "delete the email"])
        or ("mark" in text_lower
            and any(w in text_lower for w in ["handled", "done", "read"]))):
        return "EMAIL_MANAGEMENT"

    if ("search" in text_lower or "who is" in text_lower
            or "what is" in text_lower or "find" in text_lower
            or "google" in text_lower):
        return "WEB_SEARCH"

    return "LLM_BRAIN"

routing_cases = [
    # (query, expected_route, description)
    ("What's my day look like?",
     "CALENDAR_READ",  "Calendar read — natural phrasing"),
    ("What do I have on today?",
     "CALENDAR_READ",  "Calendar read — 'what do I have'"),
    ("Summarize my emails",
     "EMAIL_SUMMARY",  "Email summary — direct"),
    ("Read my emails",
     "EMAIL_SUMMARY",  "Email summary — 'read'"),
    ("Find emails from Sarah",
     "EMAIL_SEARCH",   "Email search"),
    ("Reply to the last email saying I'll call you back",
     "EMAIL_REPLY",    "Email reply with message"),
    ("Archive that email",
     "EMAIL_MANAGEMENT", "Email archive"),
    ("Mark that handled",
     "EMAIL_MANAGEMENT", "Mark handled"),
    ("Trash that email",
     "EMAIL_MANAGEMENT", "Email trash"),
    ("Remind me to order dog food",
     "TASK",           "Task creation — 'remind me'"),
    ("Add to my list: call dentist",
     "TASK",           "Task creation — 'add to my list'"),
    ("What's on my list?",
     "TASK",           "Task list"),
    ("My tasks",
     "TASK",           "Task list — short form"),
    ("Did I ever order that dog food?",
     "TASK_RECALL",    "Memory recall — 'did I ever'"),
    ("Have I called David back?",
     "TASK_RECALL",    "Memory recall — 'have I'"),
    ("Book a call with David tomorrow afternoon",
     "CALENDAR_ACTION", "Calendar create — 'book'"),
    ("Cancel my 2pm meeting",
     "CALENDAR_ACTION", "Calendar cancel"),
    ("Schedule a meeting with the team on Friday",
     "CALENDAR_ACTION", "Calendar create — 'schedule a meeting'"),
    ("Move the first one to Thursday",
     "CALENDAR_ACTION", "Calendar move"),
    ("What's the weather like today?",
     "WEATHER",        "Weather query"),
    ("Who are you?",
     "SELF_KNOWLEDGE", "Self-knowledge query"),
    ("What do you know about me?",
     "SELF_KNOWLEDGE", "Self-knowledge — 'about me'"),
    ("What is Python?",
     "WEB_SEARCH",     "Web search — 'what is'"),
    ("Search for best practices in REST APIs",
     "WEB_SEARCH",     "Web search — 'search for'"),
    ("Show me the latest optimization report",
     "REPORT_RETRIEVAL", "Report retrieval"),
    ("Optimize the jarvis_main.py file and write a doc",
     "CODE_OPTIMIZATION", "Code optimization"),
    ("Good morning",
     "LLM_BRAIN",      "General conversation → LLM"),
    ("Tell me a joke",
     "LLM_BRAIN",      "General conversation → LLM"),
    ("How are you feeling today Jarvis?",
     "LLM_BRAIN",      "General conversation → LLM"),
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
