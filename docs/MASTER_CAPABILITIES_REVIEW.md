# MASTER CAPABILITIES REVIEW

Date: 2026-02-14
Primary Spec: `docs/jarvis spec.md`
Target Runtime: `jarvis_main.py`

## Executive Summary
This document compares current Jarvis GT2 behaviour against the intended behavioural spec. The system is strong in core operational workflows (voice routing, web/email/task flows, reminders, dashboard integration), but still has shortfalls in fully natural assistant behaviour and modular maintainability.

## Current Architecture Use
- Runtime orchestration is centralized in `JarvisGT2` (`jarvis_main.py:382`).
- Input stack: wake word + VAD + OpenVINO Whisper STT (NPU preferred).
- Router stack: contextual resolver, intent scoring, then LLM fallback (`process_conversation` at `jarvis_main.py:4522`).
- Action domains: email, calendar, tasks, web/news, vault, system specs.
- UI stack: websocket dashboard bridge (state/metrics/logs/focus/ticker).
- Persistence: JSON memory, memory index, health snapshot/log, vault index + semantic vector cache.
- LLM stack: fast/smart tier routing via Brain PC endpoint (`call_smart_model` at `jarvis_main.py:1510`).

## Behaviour Coverage vs Spec

### 1. Conversation Continuity
- Working:
- `process_conversation` multi-stage routing (`jarvis_main.py:4522`).
- Context key resolver for `e1/wr1/c1/news 1` (`_handle_contextual_command` at `jarvis_main.py:1736`).
- Partial:
- Still keyword/regex heavy in some routes; non-command phrasing can miss.

### 2. Email Assistant
- Working:
- Summary/search/reply/archive patterns (`handle_email_summary_request` `jarvis_main.py:1280`, `handle_email_search_request` `jarvis_main.py:1477`).
- High-priority webhook queue + conversational follow-up.
- Partial:
- Some summary paths still rely on LLM availability for best output quality.

### 3. Calendar & Reminders
- Working:
- Authoritative calendar read/action handlers now implemented (`handle_calendar_read` `jarvis_main.py:3454`, `handle_calendar_action` `jarvis_main.py:3501`).
- Relative time parsing and task reminder scheduler (`reminder_scheduler_loop` `jarvis_main.py:4863`).
- Partial:
- No offline calendar cache if Google API unavailable.

### 4. Knowledge & Memory
- Working:
- Persistent memory + indexed action ledger + session context.
- Health logs/snapshot now actively influence health responses.
- Partial:
- Data spread across multiple stores still needs stronger consistency contracts.

### 5. Notification & Attention Management
- Working:
- Notification queue, cooldown, command capture lock.
- 2-hour health break reminder tied to latest health log (scheduler path).
- Partial:
- Queue policy still mixed between immediate and delayed speaking paths.

### 6. Action Assistance
- Working:
- Task create/list/complete/recall (`handle_task_request` `jarvis_main.py:5003`).
- Comparison/report generation now added (`handle_comparison_request` `jarvis_main.py:2300`).
- Partial:
- Multi-step composition quality varies by utterance style.

### 7. Context Awareness
- Working:
- Session addressing and natural ordinal mapping.
- Contextual actions across email/web/news/docs.
- Partial:
- Broader pronoun chaining across long sessions can still degrade.

### 8. Personality / Response Style
- Working:
- Concise mode and health-aware adaptation.
- Tiered model routing for latency/quality balance.
- Partial:
- Some responses can still drift verbose without strict post-processing.

## Shortfalls Against Spec
1. The assistant still behaves command-first in edge phrasing instead of fully conversational inference.
2. Monolithic runtime class increases regression risk and slows targeted iteration.
3. LLM dependency remains high for some narrative outputs that could be deterministic.
4. Encoding/mojibake legacy literals remain in source and are currently mitigated at runtime normalization layer.
5. Calendar and email reliability still tied to external service uptime without local cache/replay layer.

## Code Areas Needing Optimization
1. `jarvis_main.py` monolith (high churn, high coupling).
2. Intent matching pipeline (`_match_intent`) could be precompiled for lower per-turn overhead.
3. Mixed direct `requests.post` usage should be consolidated under one model call wrapper.
4. Repeated file read + snippet patterns in search/analysis handlers can be centralized.
5. Legacy mojibake literals should be source-cleaned to remove runtime repair overhead.

## Improvement Recommendations
1. Split runtime into domain modules: `email_service`, `calendar_service`, `task_service`, `search_service`, `health_service`.
2. Keep one authoritative dispatch contract: context -> intent -> deterministic handler -> LLM assist only when needed.
3. Add deterministic post-process guards for response length and factual mode per intent.
4. Add a lightweight local event cache for calendar/email summaries to handle transient API outages.
5. Add automated behavioural test cases for comparison/calendar health timer edge conditions.

## New Capability Added in This Patch
- File comparison command now works end-to-end with line-numbered reporting and document generation.
- Handler: `handle_comparison_request` (`jarvis_main.py:2300`).

## Bottom Line
Jarvis is now materially closer to the behavioural assistant spec, with strong operational capability and improved reliability in calendar/health/comparison workflows. Remaining gaps are mostly around robustness of natural dialogue handling and maintainability at current code scale.
