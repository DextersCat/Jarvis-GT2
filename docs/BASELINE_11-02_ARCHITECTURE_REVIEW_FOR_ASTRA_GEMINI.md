# Jarvis GT2 Baseline 11-02 - Architecture and Behavioural Gap Report

Date: 2026-02-11  
Baseline commit: `2aecb9f` (`baseline-11-02`)  
Primary spec reviewed: `docs/jarvis spec.md`

## 1. Purpose and Scope
This document evaluates the current Jarvis GT2 implementation against the behavioural requirements in `docs/jarvis spec.md`, and summarizes functional/code weaknesses in the current baseline.

This is not a redesign document. It focuses on what the current system does, where behaviour deviates from the spec, and what immediate corrective work can be done within the existing codebase.

## 2. High-Level System Map
Current runtime is centered around one large process (`JarvisGT2` in `jarvis_main.py`) plus a dashboard websocket bridge.

Key runtime components:
- Voice input and wake-word loop: `JarvisGT2` (`jarvis_main.py:307`, wake/listen methods in same file)
- Core command routing: `process_conversation` (`jarvis_main.py:2929`)
- Email actions and summaries: `handle_email_summary_request` (`jarvis_main.py:1036`), `handle_email_search_request` (`jarvis_main.py:1196`), `handle_email_reply_request` (`jarvis_main.py:1325`)
- Contextual short-key resolver: `_handle_contextual_command` (`jarvis_main.py:1396`)
- Web/deep-dig flows: `handle_web_search` (`jarvis_main.py:1498`), `handle_deep_dig` (`jarvis_main.py:1548`)
- Notifications/webhooks: `handle_n8n_webhook` (`jarvis_main.py:2060`), Flask webhook setup (`jarvis_main.py:3427`)
- Reminder scheduler: `reminder_scheduler_loop` (`jarvis_main.py:3744`)
- Dashboard bridge telemetry: `DashboardBridge` (`dashboard_bridge.py`), `_metrics_loop` (`dashboard_bridge.py:167`), `push_focus` (`dashboard_bridge.py:289`), `update_ticker` (`dashboard_bridge.py:309`)
- Session + ledger helpers: `core/context_manager.py`

Complexity profile:
- `jarvis_main.py`: 3816 lines, 74 methods
- `dashboard_bridge.py`: 321 lines
- `core/context_manager.py`: 64 lines

## 3. Behavioural Compliance vs Spec

### 3.1 Summary Rating
- Conversation continuity: Partially implemented
- Email assistant: Partially implemented
- Calendar/reminder assistant: Partially implemented
- Persistent knowledge/memory: Partially implemented
- Notification attention management: Partially implemented
- Action assistance (tasks/notes): Partially implemented
- Context awareness across time: Partially implemented
- Butler-style personality constraints: Partially implemented

### 3.2 Detailed Matrix

1. Conversation (spec section 1)
- Working:
  - Maintains a short context buffer (`add_to_context`, `get_context_history`, `jarvis_main.py:1808` onward).
  - Supports follow-up style via short-key commands (`show e1`, `open wr1`) through `_handle_contextual_command` (`jarvis_main.py:1396`).
- Partial:
  - Most routing is still keyword/phrase based in `process_conversation` (`jarvis_main.py:2929`), so non-command natural phrasing is inconsistent.
- Missing/incorrect:
  - Intent definition table (`INTENTS`) exists (`jarvis_main.py:246`) but is not the active router in production path.
  - `_route_by_context` is declared but empty (`jarvis_main.py:1772`), reducing conversational continuity.

2. Email Assistant (spec section 2)
- Working:
  - Email summary/search/reply/archive/trash handlers exist and execute.
  - Pending reply confirmation path exists (`check_pending_confirmation`).
  - Session key population for email items (`e1`, `e2`) now integrated in summary/search flows.
- Partial:
  - Prioritization logic exists but still rule-based and not strongly purpose-aware (important vs noise judgement is basic).
- Missing/incorrect:
  - High-priority queue items created in webhook handler do not consistently carry a `priority` field when queued (`jarvis_main.py:2080`, `jarvis_main.py:2090`), while idle-alert scanner expects `item['priority'] == 'HIGH'` (`jarvis_main.py:3783`). This can suppress expected idle escalation behaviour.
  - Notification speaking can interrupt user-desired continuity in active workflows, as observed in your runtime logs.

3. Calendar & Reminders (spec section 3)
- Working:
  - Relative datetime parser exists and covers core phrases.
  - Task reminder scheduler exists and runs in background.
- Partial:
  - Calendar integration has both placeholder and action paths in the file; behaviour can be inconsistent depending on route hit.
- Missing/incorrect:
  - Natural modifications like “add 30 minutes travel time” are not robustly represented end-to-end.

4. Knowledge & Memory (spec section 4)
- Working:
  - Persistent memory files and index are integrated.
  - Conversational ledger and session context objects exist and are used in active flows.
- Partial:
  - Memory is mixed between multiple structures (`memory`, `memory_index`, session context); consistency of retrieval/update semantics is uneven.
- Missing/incorrect:
  - Some memory-based personalized guidance in the spec is not systematically enforced in all intents.

5. Notifications & Attention Management (spec section 5)
- Working:
  - Notification queue and webhook ingestion exist.
  - Cooldown for high-priority speech exists.
- Partial:
  - Grouped summarization is present in places but not globally coordinated across all channels.
- Missing/incorrect:
  - Queue item schema mismatch (priority handling noted above) reduces reliable escalation filtering.
  - No global “do not interrupt current assistant response except URGENT” gate applied uniformly.

6. Action Assistance (spec section 6)
- Working:
  - Task create/list/complete/recall methods are present and wired.
- Partial:
  - Behavioural phrasing handling is improved but still command-heavy.
- Missing/incorrect:
  - Action chaining (email + reminder + calendar in one conversational turn) is not uniformly orchestrated.

7. Context Awareness (spec section 7)
- Working:
  - Short-key context (`wr1/e1/d1/c1`) works for targeted follow-ups.
- Partial:
  - Some pronoun/anaphora handling still depends on exact phrasing instead of robust context inference.
- Missing/incorrect:
  - Empty `_route_by_context` leaves a known context gap in follow-up behaviour.

8. Personality (spec section 8)
- Working:
  - Most spoken responses are concise and practical.
- Partial:
  - Some paths still generate verbose assistant-like summaries.
- Missing/incorrect:
  - Style consistency depends heavily on handler; not centrally enforced.

## 4. Code-Level Findings (Functional Risk)

### Critical
1. Router split/legacy drift
- `process_conversation` remains a large mixed legacy router (`jarvis_main.py:2929`) while `INTENTS` table is defined but not the authoritative runtime router (`jarvis_main.py:246`).
- User impact: unpredictable route selection and inconsistent natural-language handling.

2. Incomplete contextual route hook
- `_route_by_context` is a stub (`jarvis_main.py:1772`).
- User impact: missed follow-up understanding for “that/it/the first one” style commands.

3. Notification priority schema mismatch
- Queueing code for high/routine notifications does not always include priority metadata (`jarvis_main.py:2080`, `2090`), but scheduler filter requires it (`jarvis_main.py:3783`).
- User impact: priority idle alerts may not trigger as intended.

### High
4. Monolithic class concentration
- `JarvisGT2` hosts most cross-cutting concerns (audio, routing, email, calendar, memory, UI bridge, webhooks).
- User impact: regression risk is high; small changes can affect unrelated behaviour.

5. Fallback path quality issue
- `fallback_to_llm` body is malformed/abruptly truncated by indentation adjacency with `health_intervener` (`jarvis_main.py:1795` onward).
- User impact: unclear fallback guarantees in edge routes.

### Medium
6. Multiple behaviour contracts in one file
- Placeholder and production-like handlers coexist (e.g., calendar read placeholders plus richer action handlers).
- User impact: inconsistent observable behaviour by phrase variant.

7. Test harness fragility
- Test scripts still include environment-specific assumptions (example: missing modules/encoding constraints observed in previous runs).
- User impact: “green tests” are not always reproducible.

## 5. Dashboard/Telemetry Status

What is working now:
- NPU and Ollama gauges are present in the frontend metric schema and gauges.
- Ticker plumbing exists end-to-end (`update_ticker` in bridge + server/client handling).
- Focus panel updates are functioning in silent flow tests.

Open telemetry quality gaps:
- End-to-end timing points are not yet uniformly logged at all stages for every workflow.
- Dashboard delivery confirmation is implicit (send-only), not explicitly acknowledged per event.

## 6. Immediate Non-Architectural Remediation Backlog
This list avoids introducing new architecture/technology and focuses on behavioural correctness.

1. Make one router authoritative
- Consolidate active runtime routing so `process_conversation` and declared intent capabilities do not diverge.

2. Implement `_route_by_context`
- Fill follow-up routing for pronouns and ordinal references using existing `last_intent`, `last_calendar_events`, `session_context`.

3. Normalize notification queue schema
- Ensure every queued item includes a normalized priority field used by scheduler filters.

4. Harden non-interrupt policy
- Defer non-urgent notification speech while core assistant output is in progress; flush after completion.

5. Standardize timing instrumentation
- Add timestamped stage logs for: request start, external I/O complete, model complete, dashboard push complete.

6. Add reproducible behavioural regression script
- Keep silent live-session runner as baseline behavioural CI gate for top flows.

## 7. One-Hour Observability Plan (for next run)
Use existing logging infrastructure and add deterministic stage markers:

Per workflow, log these fields:
- `flow_id`
- `intent`
- `t_start`
- `t_fetch_done`
- `t_model_done`
- `t_dashboard_push`
- `t_speak_start`
- `t_speak_end`
- `queue_depth_before` / `queue_depth_after`
- `memory_size_tasks`, `memory_index_actions_count`

Aggregate after 1 hour:
- p50/p90/p99 latency by intent
- first-hit vs warmed-hit latency
- notification interruption count
- queue backlog max depth
- memory growth deltas (`jarvis_memory.json`, `jarvis_memory_index.json`)

## 8. Final Assessment for Astra/Gemini Review
Current baseline is functional for key user-visible paths, including silent execution of the live test flows. However, behavioural correctness is still partially constrained by legacy routing and incomplete contextual hooks.

Primary blockers to full spec fidelity are not missing integrations, but consistency issues:
- multiple routing paradigms in one runtime path
- incomplete context route implementation
- queue schema inconsistency for priority handling

Fixing those within current structure should materially improve assistant-like behaviour without major structural changes.
