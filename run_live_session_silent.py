import os
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from core.context_manager import ShortKeyGenerator, SessionContext, ConversationalLedger
from jarvis_main import JarvisGT2


class FakeMemoryIndex:
    def __init__(self):
        self.actions = []

    def add_action(self, action_type, description, metadata=None):
        item = {
            "action_type": action_type,
            "description": description,
            "metadata": metadata or {},
            "timestamp": datetime.now().isoformat(),
        }
        self.actions.append(item)
        return item

    def search_by_type(self, action_type, limit=1):
        hits = [a for a in self.actions if a.get("action_type") == action_type]
        return list(reversed(hits))[:limit]

    def search_by_keyword(self, keyword, limit=3):
        key = keyword.lower()
        hits = [a for a in self.actions if key in a.get("description", "").lower()]
        return list(reversed(hits))[:limit]


class DashboardProbe:
    def __init__(self):
        self.focus_calls = []
        self.ticker_calls = []
        self.state_calls = []

    def push_focus(self, content_type, title, content):
        self.focus_calls.append((content_type, title, content))

    def update_ticker(self, items):
        self.ticker_calls.append(items)

    def push_state(self, **kwargs):
        self.state_calls.append(kwargs)

    def set_last_ollama_response_time(self, ms):
        pass

    def set_transcribing_status(self, status):
        pass


def build_jarvis_for_silent_tests():
    with patch("jarvis_main.JarvisGT2.__init__", return_value=None):
        j = JarvisGT2()

    j.short_key_generator = ShortKeyGenerator()
    j.session_context = SessionContext()
    j.memory_index = FakeMemoryIndex()
    j.conversational_ledger = ConversationalLedger(j.memory_index, j.short_key_generator)
    j.dashboard = DashboardProbe()
    j.log = MagicMock()
    j.speak_with_piper = MagicMock()
    j.status_var = SimpleNamespace(set=lambda _x: None)

    j.memory = {"facts": [], "projects": {}, "tasks": []}
    j.tasks = []
    j.context_buffer = []
    j.pending_reply = None
    j.pending_calendar_title = None
    j.last_intent = None
    j.last_calendar_events = []
    j.last_email_context = None
    j.notification_queue = []
    j.queue_lock = SimpleNamespace(__enter__=lambda s: None, __exit__=lambda s, a, b, c: None)
    j.last_interaction_time = 0
    j.is_speaking = False
    j.gaming_mode = False
    j.interaction_count = 0
    j.last_break_time = 0
    j.vault_root = os.getcwd()
    j.active_project = "New_Jarvis"

    j.save_memory = lambda *args, **kwargs: None
    j.health_intervener = lambda: False
    j.detect_and_switch_project = lambda _t: False

    j.vault = SimpleNamespace(
        get_file=lambda key: {
            "main": "jarvis_main.py",
            "config": "config.template.json",
            "startup": "jarvis_main.py",
            "ear": "jarvis_ear.py",
        }.get(key),
        search_file=lambda name: name if os.path.exists(name) else None,
    )

    j.get_file_content = lambda filename: {"filename": filename, "content": "print('hello')\n"}
    j.write_optimization_to_doc = lambda filename, report_content: {
        "success": True,
        "doc_id": "doc-1",
        "doc_url": "https://docs.google.com/document/d/doc-1",
        "title": f"Optimization Report - {filename}",
    }
    j.call_smart_model = MagicMock(return_value="Optimisation summary for test.")

    # Search + email mocks
    j.google_search = MagicMock(return_value=[
        {"title": "Python Decorators Guide", "snippet": "A deep tutorial on decorators.", "link": "https://example.com/decorators"},
        {"title": "Decorator Patterns", "snippet": "Practical patterns.", "link": "https://example.com/patterns"},
    ])
    j.get_recent_emails = MagicMock(return_value=[
        {"id": "m1", "sender": "Alice <alice@example.com>", "subject": "Build Update", "snippet": "Looks good to me."},
        {"id": "m2", "sender": "Bob <bob@example.com>", "subject": "Follow up", "snippet": "Need one fix."},
    ])
    j.search_emails = MagicMock(return_value=[
        {"id": "s1", "sender": "spencer <spencer@example.com>", "subject": "Session check", "snippet": "Please confirm dashboard."},
    ])
    j.reply_to_email = MagicMock(return_value=True)
    j.archive_email = MagicMock(return_value=True)
    j.trash_email = MagicMock(return_value=True)

    return j


def run():
    j = build_jarvis_for_silent_tests()
    results = []

    # 1) Core Analysis Workflow
    j.process_conversation("Analyse your main file, and create an optimisation summary.")
    has_focus = any("Optimization Report" in t or "[c" in t for _, t, _ in j.dashboard.focus_calls)
    results.append(("Test 1: Core Analysis Workflow", has_focus))

    # 2) GUI & Performance Metrics (code-level verification)
    gauges_ok = True
    gauges_file = "GUI/Cyber-Grid-Dashboard/client/src/components/system-gauges.tsx"
    with open(gauges_file, "r", encoding="utf-8") as f:
        gauges_src = f.read()
    gauges_ok &= 'label="NPU"' in gauges_src
    gauges_ok &= 'label="GT2 -> Ollama"' in gauges_src
    results.append(("Test 2: GUI & Performance Metrics", gauges_ok))

    # 3.1 Flow 1 (Web Search -> Deep Dig)
    with patch("jarvis_main.requests.get") as mock_get:
        mock_get.return_value.raise_for_status = lambda: None
        mock_get.return_value.text = "<html><body><h1>Decorators</h1><p>Detailed content.</p></body></html>"
        j.process_conversation("search the web for python decorators")
        j.process_conversation("dig deeper into wr1")
    flow_31 = j.session_context.get_item("d1") is not None
    results.append(("Test 3.1: Flow 1 (Web Search -> Deep Dig)", flow_31))

    # 3.2 Flow 2 (Email Summary -> Reply -> Yes)
    with patch("jarvis_main.requests.post") as mock_post:
        mock_post.return_value.json.return_value = {"response": "Email summary output."}
        j.process_conversation("summarize my emails")
    j.process_conversation("reply to e1 saying looks good")
    j.process_conversation("yes")
    flow_32 = j.reply_to_email.called
    results.append(("Test 3.2: Flow 2 (Email Summary -> Reply)", flow_32))

    # 3.3 Flow 3 (Code Optimization -> Retrieve)
    j.process_conversation("analyze the config file and create a report")
    j.process_conversation("show me c1")
    flow_33 = any("[c1]" in title.lower() or "c1" in title.lower() for _, title, _ in j.dashboard.focus_calls)
    results.append(("Test 3.3: Flow 3 (Code Optimization -> Retrieve)", flow_33))

    # 3.4 Flow 5 (Task Management)
    j.process_conversation("add a task to test the new build")
    j.process_conversation("what's on my list")
    j.process_conversation("mark task 1 done")
    flow_34 = any(t.get("done") for t in j.tasks)
    results.append(("Test 3.4: Flow 5 (Task Management)", flow_34))

    # 3.5 Flow 7 (Email Search -> Display)
    j.process_conversation("find emails from spencer")
    j.process_conversation("show e1")
    flow_35 = any(ct == "email" and "[e1]" in title.lower() for ct, title, _ in j.dashboard.focus_calls)
    results.append(("Test 3.5: Flow 7 (Email Search -> Display)", flow_35))

    all_pass = all(status for _, status in results)
    date_str = datetime.now().strftime("%B %d, %Y")

    lines = [
        "# Jarvis GT2 - Live Test Session Results",
        "",
        f"**Date**: {date_str}",
        "**Objective**: Silent verification of live command flows without microphone interaction.",
        "",
        "---",
        "",
        "## Test Plan & Results",
        "",
    ]
    for name, status in results:
        lines.append(f"### {name}")
        lines.append("")
        lines.append(f"* **Status**: `{'PASSED' if status else 'FAILED'}`")
        lines.append("")

    lines.extend([
        "---",
        "",
        "## Session Summary",
        "",
        f"* **Overall Status**: `{'PASSED' if all_pass else 'FAILED'}`",
        "* **Notes**: Results generated via `run_live_session_silent.py` using mocked external services and real command routing.",
        "",
    ])

    with open("LIVE_TEST_SESSION.md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print("Silent live session complete.")
    for name, status in results:
        print(f"- {name}: {'PASSED' if status else 'FAILED'}")
    print(f"Overall: {'PASSED' if all_pass else 'FAILED'}")
    return 0 if all_pass else 1


if __name__ == "__main__":
    raise SystemExit(run())
