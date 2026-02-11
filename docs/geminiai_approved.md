🛡️ J.A.R.V.I.S. GT2 - Master Refactor & Visual Alignment Plan
Phase 1: Core Architectural Refactor (The Brain)
1. Persistent Conversational Ledger & Short-Key Indexing
Goal: True long-term memory with human-readable "Addresses."

Task: Implement the ConversationalLedger using the memory_index.py database.

Short-Key Protocol: Every interaction is assigned a persistent key: [Date]-[Type][Counter].

e (Email), w (Web), d (Doc), c (Code/Vault), h (Health), q (Query).

Example: 20260211-e3 (The 3rd email interaction of the day).

The Ledger: A searchable history where Jarvis can "recall" any specific Short-Key from the last 3 months.

2. Volatile SessionContext & Contextual Resolver
Goal: Enable follow-ups like "Reply to e3" or "Summarise wr1."

Task: Create the SessionContext object as the "Working Memory."

The Resolver: A regex-based listener in process_conversation that intercepts Short-Keys.

If you say "Open e3," the Resolver looks up the metadata for that index in the current session and triggers the correct tool (e.g., Gmail get_message) without needing the subject line or sender name.

3. GT2 Hardware Acceleration (NPU/OpenVINO)
Goal: Zero-latency transcription using the GT2’s Intel AI Boost.

Task: Replace standard Whisper with openvino-whisper. Add a diagnostic check to ensure the NPU is handling the transcription loop.

Phase 2: Visual Interface & Navigation (The Face)
4. Dashboard Ticker Tape (Visual Hints)
Goal: Glanceable navigation of active indexes.

Task: Implement a horizontal scrolling "Ticker" at the bottom of the Cyber-Grid Dashboard.

Logic: When Jarvis returns a list of emails or web results, the Ticker populates with the Short-Keys:

Display: [e1: Bev] [e2: Amazon] [e3: Meeting] ...

Benefit: Reduces anxiety by ensuring you never have to "guess" which number corresponds to which email.

5. Context Panel Integration (The Addressing System)
Goal: All displayed items must have visible "Handles."

Task: Refactor the Dashboard Focus/Context Panel to prefix all items with their Short-Keys.

Web Results: Displayed as [wr1], [wr2], etc.

Docs: Displayed as [d1], [d2], etc.

Interactive Link: Any item displayed in the panel is automatically injected into the SessionContext for immediate follow-up.

Phase 3: Feature Overhaul (The Agency)
6. "Deep Dig" Web Interaction
Problem: Web searches are currently "dead ends."

The Task: If results wr1 through wr5 are on screen, you can say: "Jarvis, dig deeper into wr2."

The Workflow: Jarvis uses the URL stored in wr2 to perform a targeted scrape and analysis, pushing the new data to the Focus Panel.

7. Attention & Notification Management
Goal: Respectful, persistent notifications.

Task: n8n email alerts are stored in the Ledger. If you are idle for 60 seconds, Jarvis announces: "Sir, you have a priority email [e4] from Kent Robotics. Shall I display it?"

Phase 4: Quality & Verification
8. Automated Pre-flight "Recall" Tests
Task: Add a test suite to preflight_test.py that simulates a multi-turn conversation:

Search for code files (c1, c2).

Request: "Analyse c2."

Verify: Does the Scribe report use the content of the correct file?