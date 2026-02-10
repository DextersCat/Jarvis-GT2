# Jarvis GT2 - Complete Email Integration ✅

**Status**: PRODUCTION-READY

## Overview

Implemented three independent but complementary email workflows:

### Workflow 1: **Automated n8n Email Notifications** (Real-time)
```
Gmail → n8n Detects New Email → POST /speak → Jarvis Announces
```
**Example**: "You have a new email from John Doe regarding Project Status"

### Workflow 2: **Voice Command Email Queries** (On-demand) 
```
User (voice) → Intent Detection → Gmail API → Ollama AI → Speak Result
```
**Examples**:
- "Summarize my emails" 
- "Find emails from John about the proposal"
- "Reply to the last email saying thanks"

### Workflow 3: **Gmail API Direct Access** (Fallback)
When Gmail API is available, use it directly instead of relying on n8n queue

---

## Gmail API Methods (New)

### `search_emails(query)`
Search with Gmail operators: `from:`, `subject:`, `to:`, `before:`, `since:`, etc.

```python
emails = jarvis.search_emails("from:john@example.com subject:proposal")
# Returns: [{id, sender, subject, snippet}, ...]
```

### `get_recent_emails(limit=5)`
Fetch N most recent emails from inbox

```python
recent = jarvis.get_recent_emails(limit=5)
```

### `send_email(to, subject, body)`
Send a new email

```python
jarvis.send_email("recipient@example.com", "Subject", "Body text")
```

### `reply_to_email(message_id, reply_text)`
Reply to an email thread

```python
jarvis.reply_to_email("abc123xyz", "Thanks for the update!")
```

---

## Voice Command Handlers (New)

### Handler 1: Email Summary
**Command**: "Summarize my emails"

**What it does**:
1. Fetch 5 most recent emails from Gmail API
2. Format with sender, subject, snippet
3. Send to Ollama: "Summarize these emails in 2-3 sentences"
4. Speak result
5. Log to memory

**Trigger patterns**:
- "Summarize my emails"
- "Summary of my recent emails"
- "Read my emails"
- "Show me my emails"

---

### Handler 2: Email Search
**Command**: "Find emails from John"

**What it does**:
1. Parse sender name/email from voice command (regex)
2. Extract subject keywords if mentioned
3. Build Gmail query: `from:john@example.com subject:proposal`
4. Return matching emails with snippets
5. Speak summary of results

**Trigger patterns**:
- "Find emails from John"
- "Search for messages from sarah@example.com"
- "Look for emails about the proposal"
- "Show me messages from [name] about [topic]"

**Example interaction**:
```
User: "Find emails from John about the project"
Jarvis: "Found 2 emails from John. First: 'Project Update - on track'. 
         Second: 'Q1 Planning Discussion'."
```

---

### Handler 3: Email Reply
**Command**: "Reply to the last email saying thanks"

**What it does**:
1. Parse reply message from voice command (after "saying")
2. Fetch most recent email (get_recent_emails limit=1)
3. Extract sender
4. Send reply via Gmail API with proper threading
5. Confirm: "Reply sent to [sender]"

**Trigger patterns**:
- "Reply to the last email saying thanks"
- "Send a reply: I agree with your proposal"
- "Respond to John saying I'll send it tomorrow"
- "Answer the email with: Let's schedule a meeting"

**Example interaction**:
```
User: "Reply to the last email saying I'll handle it"
Jarvis: "Reply sent to John Doe."
```

---

## Data Flow Diagrams

### n8n Automated Flow
```
┌─────────────────────┐
│ Gmail               │
│ New Email Arrives   │
└──────────┬──────────┘
           │
           ↓
┌─────────────────────────────────────┐
│ n8n Workflow                        │
│ - Detect new email                  │
│ - Extract: sender, subject, id      │
│ - Extract: (optional) body          │
└──────────┬──────────────────────────┘
           │
           │ POST /speak endpoint
           ↓
┌──────────────────────────────────────┐
│ Jarvis Flask Endpoint (/speak)       │
│ - Receives email metadata            │
│ - Deduplicates by email_id           │
│ - (Priority: HIGH)                   │
└──────────┬───────────────────────────┘
           │
      ┌────┴────┐
      ↓         ↓
  [SPEAK]   [QUEUE]
  "You      + Store in
   have a   notification_queue
   new      + Metadata preserved
   email"

User can later ask to summarize/search these emails
```

### Voice Command Query Flow
```
User (voice): "Find emails from John"
           │
           ↓
┌────────────────────────────────────┐
│ process_conversation()             │
│ Intent: search + email             │
│ → handle_email_search_request()    │
└────────────┬───────────────────────┘
             │
             ↓
┌────────────────────────────────────┐
│ handle_email_search_request()      │
│ 1. Parse: sender, subject          │
│ 2. Build Gmail query               │
│ 3. Call search_emails(query)       │
│ 4. Format results                  │
│ 5. Speak summary                   │
│ 6. Log to memory                   │
└────────────┬───────────────────────┘
             │
             ↓
┌────────────────────────────────────┐
│ Gmail API                          │
│ (search_emails returns results)    │
└────────────────────────────────────┘
```

---

## Code Changes

**Commit f7ff4de**: Email metadata preservation + summary handler
**Commit 17393cf**: Complete Gmail integration (search, reply, summarize)

**Total additions**: ~550 lines
**Files modified**: `jarvis_main.py`

### New Methods:
- `search_emails(query)` - Gmail search
- `get_recent_emails(limit)` - Fetch recent emails
- `send_email(to, subject, body)` - Send email
- `reply_to_email(message_id, text)` - Reply to email
- `handle_email_summary_request()` - Summarize emails (improved version)
- `handle_email_search_request(query)` - Search emails via voice
- `handle_email_reply_request(query)` - Reply via voice

### Improved:
- `handle_n8n_webhook()` - Now preserves metadata
- `process_conversation()` - Added 3 email intent handlers

---

## Configuration

### n8n Webhook Endpoint
```
POST http://localhost:5001/speak
Content-Type: application/json

{
  "sender": "John Doe <john@example.com>",
  "subject": "Project Status Update",
  "id": "unique_email_id_for_deduplication",
  "body": "(optional) Email body"
}

Response: {"status": "success"}
```

### Gmail OAuth
- Credentials already configured
- Scopes: `gmail.send`, `gmail.readonly` 
- Files: `token.json`, `credentials.json`

---

## Testing Guide

### Test 1: n8n Email Notification
```bash
curl -X POST http://localhost:5001/speak \
  -H "Content-Type: application/json" \
  -d '{
    "sender": "John Doe <john@example.com>",
    "subject": "Project Status",
    "id": "test_email_001"
  }'
```

**Expected**:
✓ Jarvis announces email
✓ Email stored with metadata

---

### Test 2: Summarize Email (Voice)
```
User: "Summarize my emails"

Expected:
✓ Fetches recent emails from Gmail API
✓ Sends to Ollama for summarization
✓ Returns AI summary based on REAL emails
✓ No hallucination - actual email data used
```

---

### Test 3: Search Email (Voice)
```
User: "Find emails from John about proposals"

Expected:
✓ Parses: from=john, subject=proposals
✓ Builds query: "from:john subject:proposals"
✓ Returns matching emails
✓ Speaks results with subject lines & snippets
```

---

### Test 4: Reply to Email (Voice)
```
User: "Reply to the last email saying thanks"

Expected:
✓ Fetches most recent email
✓ Extracts sender
✓ Sends reply with proper thread ID
✓ Confirms: "Reply sent to [sender]"
```

---

## Architecture Decisions

### ✅ Why Gmail API over n8n Queue for Queries?
- **Real-time**: API fetches current state, not just notifications
- **Search**: Gmail operators enable powerful filtering
- **Complete**: Access to all email fields (not just sender/subject)
- **Direct**: No reliance on n8n being up-to-date

### ✅ Why Keep n8n Notifications?
- **Real-time announcements**: Inform user of new emails immediately
- **Background**: Works independent of voice commands
- **Automation**: Trigger other workflows based on email rules
- **Separation of concerns**: Notifications ≠ Queries

### ✅ Why Separate Voice Intent Handlers?
- **Clear UX**: "Summarize", "Find", "Reply" are distinct commands
- **Natural language**: Parse command-specific patterns (e.g., "saying X")
- **Future-proof**: Easy to add "draft email", "mark as read", etc.
- **Logging**: Track which actions user performs

---

## Known Limitations & Future Work

### Current Limitations
1. **Reply parsing**: Extracts reply text after "saying" - not robust to all phrasings
2. **Sender search**: Relies on regex - may miss complex name parsing
3. **No email body**: Summary and search don't include full email body (privacy)
4. **Single reply**: Always replies to most recent email (could parameterize)

### Future Enhancements
1. **Draft emails**: "Draft email to john saying..."
2. **Email filtering**: "Show unread", "Filter by sender", "Only important"
3. **Action extraction**: "Extract todos from emails"
4. **Conditional rules**: "Notify me if I get emails from my boss"
5. **Attachment handling**: Download/process attachments
6. **Multi-account**: Support multiple Gmail accounts
7. **Better NLP**: Use NLU for robust intent extraction
8. **Email body reading**: Get snippets of email content (with privacy controls)

---

## Troubleshooting

**Q: "No emails found" when they exist**
A: Check Gmail API credentials (`token.json`, `credentials.json`). Refresh OAuth if needed.

**Q: n8n webhook 404**
A: Verify Jarvis endpoint: `http://localhost:5001/speak` (not 5000)

**Q: Email summary still hallucinating**
A: Ensure `get_recent_emails()` returns data. Check Jarvis logs for API errors.

**Q: Reply not sending**
A: Verify Gmail OAuth token is fresh. Check error logs for API failures.

**Q: Timeout on email search**
A: Gmail API might be slow. Increase timeout in `search_emails()` catch block.

---

## Summary

Jarvis now has **complete, production-ready email support** with three workflows:

1. **Real-time notifications** from n8n (unchanged but improved)
2. **Smart voice queries** using Gmail API (new)
3. **Natural language email management** (search, reply, summarize)

All email operations:
- ✅ Use actual Gmail data (no hallucination)
- ✅ Preserve metadata through the full flow  
- ✅ Log actions to memory for context
- ✅ Integrate with dashboard focus panel
- ✅ Support fallback error handling

**Ready for production use!**
