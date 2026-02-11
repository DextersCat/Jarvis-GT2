# ✅ Jarvis GT2 - Architectural Refactor TODO

**Objective**: Implement the approved Visual Addressing Plan to upgrade Jarvis's core architecture, visual interface, and interactive capabilities.

**Methodology**: Adhere to the **Research → Propose → Test → Verify** cycle for each module.

---

## Phase 1: Core Architectural Refactor (The Brain)

### 1.1: Persistent Conversational Ledger
- [x] **Implement `ShortKeyGenerator`**:
  - [x] Create a class/module to generate persistent keys in the format `[Date]-[Type][Counter]` (e.g., `20260211-e3`).
  - [x] Define key types: `e` (Email), `w` (Web), `d` (Doc), `c` (Code/Vault), `h` (Health), `q` (Query).
- [x] **Implement `ConversationalLedger`**:
  - [x] Create the main class to manage long-term memory.
  - [x] Integrate with `memory_index.py` for storage and retrieval.
  - [x] Implement a method to save new interactions with their generated Short-Key.
  - [x] Implement a search method to recall interactions by Short-Key (e.g., `get_by_key('20260211-e3')`).
  - [x] Ensure the ledger stores metadata required for follow-up actions (e.g., email ID, URL, file path).

### 1.2: Volatile Session Context
- [x] **Implement `SessionContext`**:
  - [x] Create a class to act as volatile "working memory" for the current session.
  - [x] Add methods to store recently generated items (e.g., web search results, emails) with their Short-Keys.
  - [x] The context should be cleared or archived at the end of a session.
- [x] **Implement `ContextualResolver`**:
  - [x] In `process_conversation`, add a regex-based listener to detect Short-Key commands (e.g., `r'^(open|reply to|summarise|analyze)\s+([ewdchq]\w+)$'`).
  - [x] When a Short-Key is detected, use `SessionContext` to look up the item's metadata.
  - [x] Trigger the appropriate tool/handler based on the item type (e.g., `e3` → `gmail_tool.get_message()`).

### 1.3: Hardware-Accelerated Transcription
- [x] **Integrate OpenVINO Whisper**:
  - [x] Research and install `openvino-whisper` and its dependencies.
  - [x] Replace the current Whisper implementation with the OpenVINO version.
  - [x] Add a diagnostic check on startup to verify that the Intel NPU (AI Boost) is being used for transcription.
  - [x] Test for latency reduction and transcription accuracy compared to the previous implementation.

---

## Phase 2: Visual Interface & Navigation (The Face)

### 2.1: Dashboard Ticker Tape
- [x] **Update `DashboardBridge`**:
  - [x] Add a new method `update_ticker(items: list)`.
  - [x] The method should accept a list of dictionaries, each containing a `short_key` and a `label`.
- [x] **Implement Ticker in UI**:
  - [x] Add a horizontal scrolling "Ticker Tape" widget at the bottom of the Cyber-Grid Dashboard.
  - [x] When Jarvis returns a list of items (emails, web results), call `DashboardBridge.update_ticker()` to populate it.
  - [x] Display format: `[e1: Bev] [e2: Amazon] [wr1: AI News] ...`

### 2.2: Context Panel Addressing
- [x] **Refactor `DashboardBridge` Focus/Context Panel**:
  - [x] Modify the method that displays items in the Focus Panel (`update_focus_panel` or similar).
  - [x] Prefix every list item with its interactive Short-Key.
  - [x] Example display:
    ```
    [wr1] New AI model released by Google
    [wr2] Python overtakes Java in new report
    ...
    ```
- [x] **Integrate with `SessionContext`**:
  - [x] Ensure that any item displayed in the Focus Panel is automatically added to the `SessionContext` for immediate follow-up.

---

## Phase 3: Feature Overhaul (The Agency)

### 3.1: "Deep Dig" Web Interaction
- [x] **Create "Deep Dig" Workflow**:
  - [x] Add intent detection for "dig deeper into [short_key]" (e.g., `... wr2`).
  - [x] When triggered, retrieve the URL for the specified web result (`wr2`) from the `SessionContext`.
  - [x] Implement a targeted web scrape and analysis function for the given URL using BeautifulSoup.
  - [x] Push the new, detailed summary to the Dashboard Focus Panel with a new Short-Key (e.g., `d1` for document/analysis).

### 3.2: Persistent Notification Management
- [x] **Update n8n Webhook Handler**:
  - [x] When a notification is received, save it to the `ConversationalLedger` with a new Short-Key (e.g., `e4`).
- [x] **Implement Idle-Time Alert**:
  - [x] Create a timer/monitor in `reminder_scheduler_loop` to track user idle time (no voice commands).
  - [x] If idle for > 60 seconds and unread HIGH priority notifications exist in the queue, trigger a voice prompt.
  - [x] Voice prompt: "Sir, you have a priority email [e4] from Kent Robotics. Shall I display it?"

---

## Phase 4: Quality & Verification

### 4.1: Automated "Recall" Test Suite
- [x] **Extend `preflight_test.py`**: (Note: Multi-stage tests moved to `multi_stage_flow_tests.py`)
  - [x] Create a new test class `TestRecallSystem` for "Recall" and contextual follow-up.
  - [x] **Test Case: Email Display**
    - [x] Simulate a list of emails, generating `e1`.
    - [x] Simulate a user request: "show e1".
    - [x] Verify that `dashboard.push_focus` is triggered with email content.
  - [x] **Test Case: Web Result Open**
    - [x] Simulate a web search generating `wr1`.
    - [x] Simulate a user request: "open wr1".
    - [x] Verify that `webbrowser.open` is triggered with the correct URL.
  - [x] **Test Case: Deep Dig Trigger**
    - [x] Simulate a web search generating `wr2`.
    - [x] Simulate a user request: "dig deeper into wr2".
    - [x] Verify that the `handle_deep_dig` workflow is correctly triggered.
- [x] **Create `multi_stage_flow_tests.py` for comprehensive integration tests**:
  - [x] **Test Case: Multi-Stage Flow (Web Search → Deep Dig → Email Summary of Deep Dig → Calendar Appointment)**
    - [x] Simulate web search, verify `wr` keys, session context, ticker, focus panel.
    - [x] Simulate "dig deeper into wr2", verify `handle_deep_dig` call, `d` key creation, session context, ticker, focus panel.
    - [x] Simulate "email summary of d1 to spencerdixon@btinternet.com", verify LLM summary generation and `send_email` call.
    - [x] Simulate "create a calendar appointment to test jarvis for 11am this morning", verify `create_calendar_event` call.
  - [x] **Test Case: Recall and Repeat Flow (Web Search → Open wr1 → New Web Search)**
    - [x] Simulate initial web search, verify `wr` keys.
    - [x] Simulate "open wr1", verify `webbrowser.open` and context preservation.
    - [x] Simulate new web search, verify session context and ticker are cleared and repopulated.
  - [x] **Test Case: Email Recall and Reply Flow (Email Summary → Reply to e1)**
    - [x] Simulate email summary, verify `e` keys.
    - [x] Simulate "reply to e1 saying thanks", verify confirmation flow and `reply_to_email` call.