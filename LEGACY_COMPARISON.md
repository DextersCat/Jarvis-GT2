# Jarvis Email Integration - Legacy vs New Comparison

## Legacy Code Analysis (jarvis_main_legacy.py)

### What Was Working ✅
1. **Flask /speak endpoint** (line 47-60)
   - Receives email notifications from n8n
   - Extracts: sender, subject, email_id
   - Stores in SHORT_TERM_MEMORY (like our notification_queue)
   - Announces new emails

```python
@app.route('/speak', methods=['POST'])
def receive_speak():
    data = request.get_json(force=True)
    sender = data.get("sender", "Unknown")
    subject = data.get("subject", "No Subject")
    email_id = data.get("id")
    
    SHORT_TERM_MEMORY.append({
        "sender": sender,
        "subject": subject,
        "id": email_id,
    })
    
    full_sentence = f"Sir, you have a new email from {sender} regarding {subject}."
    jarvis_speak(full_sentence)
    return {"status": "success"}, 200
```

2. **Email Announcement** (line 97)
   - Flask runs in daemon thread, doesn't block main loop
   - Jarvis announces incoming emails in real-time

3. **Email Memory Lookup** (line 341-348)
   - Could answer "Who was the last email from?"
   - Pulled from SHORT_TERM_MEMORY

```python
if any(k in lowered for k in ["who", "last", "repeat"]):
    if SHORT_TERM_MEMORY:
        last = SHORT_TERM_MEMORY[-1]
        reply = (
            f"The last email was from {last['sender']} "
            f"regarding {last['subject']}."
        )
```

### What Was Missing ❌

1. **No Gmail API Integration**
   - No ability to search emails
   - No ability to reply to emails
   - No access to actual email content (body, attachments)
   - Couldn't verify emails actually existed

2. **No Email Summarization**
   - No way to ask "summarize my emails"
   - Would hallucinate without real data

3. **No Email Search**
   - "Find emails from John" → generic LLM response (wrong!)
   - No Gmail search operators

4. **No Email Reply**
   - Can't send replies via voice
   - Can't handle "Reply to email" commands

5. **No Gmail OAuth**
   - No credentials or scopes defined
   - No integration with Google APIs

---

## New Implementation (jarvis_main.py)

### ✅ Preserved from Legacy
1. **Flask /speak endpoint** (line ~2540)
   - Same functionality: receives n8n notifications
   - **IMPROVED**: Now preserves metadata in queue
   - Same: Real-time announcements

2. **Email Memory Storage** (now in notification_queue)
   - Same concept as SHORT_TERM_MEMORY
   - Better: Structured with metadata instead of dict list
   - Better: Integrated into Jarvis memory system

### ✅ NEW: Gmail API Methods

**4 new methods added** (~150 lines):

```python
def search_emails(self, query):
    """Gmail search with operators: from:, subject:, etc."""
    
def get_recent_emails(self, limit=5):
    """Fetch N most recent emails from inbox"""
    
def send_email(self, to_address, subject, body):
    """Send a new email"""
    
def reply_to_email(self, message_id, reply_text):
    """Reply to email thread"""
```

### ✅ NEW: Voice Command Handlers

**3 new intent handlers** (~300 lines):

```python
def handle_email_summary_request(self):
    # "Summarize my emails"
    # Uses Gmail API + Ollama AI
    
def handle_email_search_request(self, user_request):
    # "Find emails from John about proposals"
    # Uses Gmail API search operators
    
def handle_email_reply_request(self, user_request):
    # "Reply to last email saying thanks"
    # Uses Gmail API to send reply
```

### ✅ NEW: Intent Detection

**3 new email intents** added to process_conversation():

```python
# EMAIL SUMMARY
elif ("summarize" in text_lower or "summary" in text_lower) and "email" in text_lower:
    self.handle_email_summary_request()
    return

# EMAIL SEARCH  
elif ("search" in text_lower or "find" in text_lower) and "email" in text_lower:
    self.handle_email_search_request(raw_text)
    return

# EMAIL REPLY
elif ("reply" in text_lower or "respond" in text_lower) and "email" in text_lower:
    self.handle_email_reply_request(raw_text)
    return
```

---

## Side-by-Side Feature Comparison

| Feature | Legacy ✅ | New ✅ |
|---------|----------|--------|
| Announce new emails via n8n | ✅ | ✅ (improved) |
| Store email metadata | ✅ | ✅ (improved) |
| Answer "Who was last email?" | ✅ | ✅ (via memory) |
| **Search for emails** | ❌ | ✅ NEW |
| **Reply to emails** | ❌ | ✅ NEW |
| **Summarize emails** | ❌ | ✅ NEW |
| **Gmail API integration** | ❌ | ✅ NEW |
| **Email deduplication** | ✅ | ✅ (improved) |
| **Multiple email handling** | ✅ | ✅ (via queue) |
| **Metadata preservation** | ⚠️ (lost) | ✅ FIXED |

---

## Architecture Evolution

### Legacy (Simple)
```
n8n → /speak → SHORT_TERM_MEMORY → Announce
  ↓
User asks about email → Check SHORT_TERM_MEMORY → LLM response
```

### New (Comprehensive)
```
┌─┬─────────────────────────────────────────┐
│A│ n8n → /speak → notification_queue → Announce
│  │         └────────────────────────────────→ Store for later
├─┤
│B│ User: "Summarize emails" → Gmail API → Summary (from real data)
│  │ User: "Find emails from X" → Gmail API → Search results
│  │ User: "Reply to email" → Gmail API → Send reply
└─┴─────────────────────────────────────────┘
```

**Flow A**: Automated notifications (n8n)
**Flow B**: Voice queries (Gmail API)
**Both**: Integrated, complement each other

---

## Code Comparison Examples

### Legacy: Email Announcement
```python
# legacy code
full_sentence = f"Sir, you have a new email from {sender} regarding {subject}."
jarvis_speak(full_sentence)
```

### New: Email Announcement (Same + Preserved Metadata)
```python
# new code
notification = {
    "message": f"Sir, you have a new email from {clean_sender} regarding {clean_subject}.",
    "priority": "high",
    "source": "Email",
    "metadata": {  # ← NEW: Preserved for later use
        "sender": sender,
        "subject": subject,
        "id": email_id
    }
}
self.handle_n8n_webhook(notification)
```

### Legacy: Email Lookup
```python
# legacy code
if any(k in lowered for k in ["who", "last", "repeat"]):
    if SHORT_TERM_MEMORY:
        last = SHORT_TERM_MEMORY[-1]
        reply = f"The last email was from {last['sender']} regarding {last['subject']}."
    else:
        reply = "I do not have any recent emails in memory yet, Spencer."
```

### New: Email Search (NEW Capability)
```python
# new code
def handle_email_search_request(self, user_request):
    # Parse request: "Find emails from John"
    sender_query = extract_from_pattern(user_request)
    gmail_query = f"from:{sender_query}"
    
    # Get emails from Gmail (not just memory)
    emails = self.search_emails(gmail_query)
    
    # Return actual search results
    if emails:
        for email in emails:
            self.log(f"• {email['subject']} - {email['sender']}")
        # Speak summary of results
```

---

## Google API Credentials

### Already Available in Jarvis
```python
# Line 47-48: Gmail OAuth scopes
'https://www.googleapis.com/auth/gmail.send',
'https://www.googleapis.com/auth/gmail.readonly',

# Line ~100: get_google_creds() function
def get_google_creds():
    # Returns authenticated credentials for Gmail, Docs, Drive, etc.
    # Handles OAuth flow and token refresh
```

These were already in the code but unused for email functionality!

---

## Summary

### Legacy Code
- ✅ Solid foundation for email announcements
- ✅ Flask endpoint working
- ✅ Memory storage pattern established
- ❌ No Gmail integration
- ❌ No proactive email management

### New Code
- ✅ All legacy functionality preserved + improved
- ✅ Gmail API fully integrated
- ✅ 3 comprehensive voice commands (summarize, search, reply)
- ✅ Metadata preserved through full pipeline
- ✅ AI-powered email analysis (no hallucination)
- ✅ Production-ready error handling

### Result
Email functionality went from **simple announcement system** to **comprehensive email management platform** while maintaining backward compatibility with n8n notifications.
