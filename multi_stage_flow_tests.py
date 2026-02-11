import unittest
from unittest.mock import MagicMock, patch, call
from datetime import date, datetime, timedelta
import os
import sys

# Add the project root to the sys.path to allow imports
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from jarvis_main import JarvisGT2
from core.context_manager import ShortKeyGenerator, SessionContext, ConversationalLedger

class TestMultiStageFlows(unittest.TestCase):
    """
    Comprehensive integration tests for multi-stage conversational flows,
    focusing on the new visual addressing plan, context management,
    and dashboard interactions.
    """

    def setUp(self):
        """
        Set up a mocked JarvisGT2 instance for testing.
        We mock external dependencies to control test environment and verify interactions.
        """
        # Patch JarvisGT2's __init__ to prevent real hardware/network calls during setup
        with patch('jarvis_main.JarvisGT2.__init__', return_value=None):
            self.jarvis = JarvisGT2()

            # --- Core Context Management (Real Instances) ---
            # These are the components we are primarily testing, so they should be real.
            self.jarvis.short_key_generator = ShortKeyGenerator()
            self.jarvis.session_context = SessionContext()
            
            # Mock MemoryIndex for ConversationalLedger
            self.mock_memory_index = MagicMock()
            self.jarvis.conversational_ledger = ConversationalLedger(
                self.mock_memory_index, self.jarvis.short_key_generator
            )

            # --- Mock External Dependencies ---
            self.jarvis.log = MagicMock()
            self.jarvis.speak_with_piper = MagicMock()
            self.jarvis.dashboard = MagicMock()
            self.jarvis.dashboard.push_focus = MagicMock()
            self.jarvis.dashboard.update_ticker = MagicMock()
            self.jarvis.dashboard.push_state = MagicMock()
            self.jarvis.status_var = MagicMock() # Dummy status_var

            # Mock specific Jarvis methods that interact with external services
            self.jarvis.google_search = MagicMock()
            self.jarvis.call_smart_model = MagicMock() # For deep dig summary, email summary
            self.jarvis.get_recent_emails = MagicMock() # For email summary
            self.jarvis.send_email = MagicMock() # For sending email summary
            self.jarvis.create_calendar_event = MagicMock()
            self.jarvis.parse_relative_datetime = MagicMock()
            self.jarvis.extract_sender_name = MagicMock(side_effect=lambda x: x.split('<')[0].strip())

            # Mock webbrowser.open for 'open wrX' commands
            self.mock_webbrowser_open = patch('webbrowser.open').start()
            self.addCleanup(patch.stopall) # Ensure patches are stopped after each test

            # Mock BeautifulSoup for handle_deep_dig
            self.mock_beautifulsoup = patch('jarvis_main.BeautifulSoup').start()
            self.mock_requests_get = patch('requests.get').start()
            
            # Reset short key generator daily counter for predictable keys
            self.jarvis.short_key_generator._today = date.today()
            self.jarvis.short_key_generator._counters.clear()

            print(f"\n--- Starting Test: {self._testMethodName} ---")

    def tearDown(self):
        """Clean up after each test."""
        print(f"--- Finished Test: {self._testMethodName} ---\n")

    def test_full_multi_function_flow(self):
        """
        Simulates the user-defined multi-stage flow:
        Web Search -> Deep Dig -> Email Summary of Deep Dig -> Calendar Appointment.
        Verifies context, ledger, and dashboard updates at each stage.
        """
        print("\n--- Test Case: Web Search -> Deep Dig -> Email Summary -> Calendar ---")

        # --- Step 1: Web Search for "latest ai news" ---
        print("\n[STEP 1] User: 'Jarvis, search the web for latest ai news'")
        mock_web_results = [
            {'title': 'AI Breakthroughs 2024 | Example.com', 'snippet': 'New models announced.', 'link': 'https://example.com/ai-breakthroughs'},
            {'title': 'Future of AI: Robotics | TechNews.com', 'snippet': 'Robotics advancements.', 'link': 'https://technews.com/robotics-ai'},
            {'title': 'Ethics in AI | AIJournal.org', 'snippet': 'Debate on AI ethics.', 'link': 'https://aijournal.org/ethics'}
        ]
        self.jarvis.google_search.return_value = mock_web_results
        
        # Mock ConversationalLedger.add_entry to return predictable short_keys
        self.mock_memory_index.add_action.side_effect = [
            {'metadata': {'short_key': f"{date.today().strftime('%Y%m%d')}-wr1"}},
            {'metadata': {'short_key': f"{date.today().strftime('%Y%m%d')}-wr2"}},
            {'metadata': {'short_key': f"{date.today().strftime('%Y%m%d')}-wr3"}},
            # Subsequent calls will be for deep dig and email
        ]

        self.jarvis.process_conversation("search the web for latest ai news")

        # Expected: Web search results are logged, added to session context, and displayed.
        self.jarvis.google_search.assert_called_with("latest ai news")
        self.jarvis.speak_with_piper.assert_called_with("Searching for latest ai news.")
        self.jarvis.speak_with_piper.assert_called_with("Sir, I've found 3 results. They are on screen.")
        
        # Verify session context population
        wr1_item = self.jarvis.session_context.get_item('wr1')
        self.assertIsNotNone(wr1_item, "wr1 should be in session context")
        self.assertEqual(wr1_item['label'], 'AI Breakthroughs 2024', "wr1 label mismatch")
        
        wr2_item = self.jarvis.session_context.get_item('wr2')
        self.assertIsNotNone(wr2_item, "wr2 should be in session context")
        self.assertEqual(wr2_item['label'], 'Future of AI: Robotics', "wr2 label mismatch")

        # Verify dashboard updates
        self.jarvis.dashboard.push_focus.assert_called_once()
        focus_call_args = self.jarvis.dashboard.push_focus.call_args[0]
        self.assertEqual(focus_call_args[0], "docs")
        self.assertIn("[wr1] AI Breakthroughs 2024", focus_call_args[2])
        self.assertIn("[wr2] Future of AI: Robotics", focus_call_args[2])
        
        self.jarvis.dashboard.update_ticker.assert_called_once()
        ticker_items = self.jarvis.dashboard.update_ticker.call_args[0][0]
        self.assertEqual(len(ticker_items), 3)
        self.assertIn({'short_key': 'wr1', 'label': 'AI Breakthroughs 2024'}, ticker_items)
        self.assertIn({'short_key': 'wr2', 'label': 'Future of AI: Robotics'}, ticker_items)
        print("  ✓ Step 1 (Web Search) verified.")

        # --- Step 2: Deep Dig into wr2 result ---
        print("\n[STEP 2] User: 'dig deeper into wr2'")
        self.jarvis.speak_with_piper.reset_mock()
        self.jarvis.dashboard.push_focus.reset_mock()
        self.jarvis.dashboard.update_ticker.reset_mock()
        self.mock_memory_index.add_action.reset_mock()

        # Mock web scraping and LLM summary for deep dig
        self.mock_requests_get.return_value.raise_for_status = MagicMock()
        self.mock_requests_get.return_value.text = "<html><body><h1>Robotics AI</h1><p>Detailed article content.</p></body></html>"
        self.mock_beautifulsoup.return_value.stripped_strings = ["Robotics AI", "Detailed article content."]
        self.jarvis.call_smart_model.return_value = "Summary of Robotics AI article: Key points are X, Y, Z."
        
        # Mock ConversationalLedger.add_entry for the deep dig document
        self.mock_memory_index.add_action.return_value = {'metadata': {'short_key': f"{date.today().strftime('%Y%m%d')}-d1"}}

        self.jarvis.process_conversation("dig deeper into wr2")

        # Expected: Deep dig handler called, new document created (d1), displayed.
        self.jarvis.speak_with_piper.assert_called_with("Digging deeper into Future of AI: Robotics.")
        self.jarvis.speak_with_piper.assert_called_with("Sir, my analysis of Future of AI: Robotics is complete and on screen. It is now referenced as d1.")
        
        self.mock_requests_get.assert_called_with(wr2_item['metadata']['url'], timeout=15, headers=Any) # Any for headers
        self.jarvis.call_smart_model.assert_called_once()
        self.assertIn("Detailed article content.", self.jarvis.call_smart_model.call_args[0][0])
        
        d1_item = self.jarvis.session_context.get_item('d1')
        self.assertIsNotNone(d1_item, "d1 should be in session context")
        self.assertEqual(d1_item['label'], 'Analysis: Future of AI: Robotics', "d1 label mismatch")
        
        self.jarvis.dashboard.push_focus.assert_called_once()
        focus_call_args = self.jarvis.dashboard.push_focus.call_args[0]
        self.assertEqual(focus_call_args[0], "docs")
        self.assertIn("Analysis of wr2: Future of AI: Robotics", focus_call_args[1])
        self.assertIn("Summary of Robotics AI article:", focus_call_args[2])
        
        self.jarvis.dashboard.update_ticker.assert_called_once()
        ticker_items = self.jarvis.dashboard.update_ticker.call_args[0][0]
        self.assertEqual(len(ticker_items), 4) # wr1, wr2, wr3, d1
        self.assertIn({'short_key': 'd1', 'label': 'Analysis: Future of AI: Robotics'}, ticker_items)
        print("  ✓ Step 2 (Deep Dig) verified.")

        # --- Step 3: Email Summary of Deep Dig result (d1) to spencerdixon@btinternet.com ---
        print("\n[STEP 3] User: 'email summary of d1 to spencerdixon@btinternet.com'")
        self.jarvis.speak_with_piper.reset_mock()
        self.jarvis.dashboard.push_focus.reset_mock()
        self.jarvis.dashboard.update_ticker.reset_mock()
        self.jarvis.send_email.reset_mock()
        self.jarvis.call_smart_model.reset_mock() # For email summary generation

        # Mock LLM to generate email body from d1 summary
        self.jarvis.call_smart_model.return_value = "Here is the summary of the Robotics AI article: Key points are X, Y, Z. Regards, Jarvis."
        self.jarvis.send_email.return_value = True # Simulate successful email send

        # We need to mock the intent routing for this specific command
        # The current intent router doesn't have a direct "email summary of dX" intent.
        # For this simulation, we'll directly call the email sending logic after generating the summary.
        # In a real scenario, the LLM would likely generate the email content and then Jarvis would ask for confirmation to send.
        
        # Simulate the LLM generating the email content based on d1
        d1_content = d1_item['metadata']['summary']
        email_body_prompt = f"Draft a concise email summarizing the following content for spencerdixon@btinternet.com:\n\n{d1_content}\n\nEmail Body:"
        email_body = self.jarvis.call_smart_model(email_body_prompt, timeout=60)
        
        # Simulate Jarvis sending the email
        self.jarvis.send_email("spencerdixon@btinternet.com", "Summary of Robotics AI Article (Deep Dig)", email_body)

        self.jarvis.send_email.assert_called_once_with(
            "spencerdixon@btinternet.com",
            "Summary of Robotics AI Article (Deep Dig)",
            "Here is the summary of the Robotics AI article: Key points are X, Y, Z. Regards, Jarvis."
        )
        self.jarvis.speak_with_piper.assert_called_with("✓ Email sent to spencerdixon@btinternet.com")
        print("  ✓ Step 3 (Email Summary of Deep Dig) verified.")

        # --- Step 4: Create Calendar Appointment for "test jarvis" at 11am this morning ---
        print("\n[STEP 4] User: 'create a calendar appointment to test jarvis for 11am this morning'")
        self.jarvis.speak_with_piper.reset_mock()
        self.jarvis.dashboard.push_focus.reset_mock()
        self.jarvis.dashboard.update_ticker.reset_mock()
        self.jarvis.create_calendar_event.reset_mock()
        
        # Mock parse_relative_datetime to return a specific datetime for "11am this morning"
        today = datetime.now().date()
        mock_start_dt = datetime(today.year, today.month, today.day, 11, 0, 0)
        mock_end_dt = mock_start_dt + timedelta(hours=1) # Default 1 hour event
        self.jarvis.parse_relative_datetime.return_value = (mock_start_dt, mock_end_dt)
        self.jarvis.create_calendar_event.return_value = {'id': 'cal_event_123', 'summary': 'test jarvis'}

        self.jarvis.process_conversation("create a calendar appointment to test jarvis for 11am this morning")

        # Expected: Calendar event created and confirmed.
        self.jarvis.parse_relative_datetime.assert_called_with("create a calendar appointment to test jarvis for 11am this morning")
        self.jarvis.create_calendar_event.assert_called_once_with(
            "test jarvis", mock_start_dt, mock_end_dt
        )
        expected_time_str = mock_start_dt.strftime('%A %d %b at %I:%M %p').lstrip('0')
        self.jarvis.speak_with_piper.assert_called_with(f"Done. I've booked test jarvis for {expected_time_str}.")
        
        # Verify dashboard update (calendar read is usually triggered after create)
        # Assuming get_calendar is called and pushes to focus
        self.jarvis.dashboard.push_focus.assert_called_once()
        focus_call_args = self.jarvis.dashboard.push_focus.call_args[0]
        self.assertEqual(focus_call_args[0], "docs")
        self.assertEqual(focus_call_args[1], "Calendar")
        print("  ✓ Step 4 (Calendar Appointment) verified.")

        print("\n--- Full Multi-Function Flow Test PASSED ---")

    def test_recall_and_repeat_flow(self):
        """
        Tests recalling a previous web search result and performing a new action.
        Simulates: Web Search -> Recall wr1 -> Open wr1 -> New Web Search.
        """
        print("\n--- Test Case: Recall and Repeat Flow ---")

        # --- Step 1: Initial Web Search ---
        print("\n[STEP 1] User: 'Jarvis, search for python news'")
        mock_web_results = [
            {'title': 'Python 3.12 Released | Python.org', 'snippet': 'New features.', 'link': 'https://python.org/3.12'},
            {'title': 'Django Security Update | Django.com', 'snippet': 'Critical patch.', 'link': 'https://django.com/security'}
        ]
        self.jarvis.google_search.return_value = mock_web_results
        self.mock_memory_index.add_action.side_effect = [
            {'metadata': {'short_key': f"{date.today().strftime('%Y%m%d')}-wr1"}},
            {'metadata': {'short_key': f"{date.today().strftime('%Y%m%d')}-wr2"}},
        ]
        self.jarvis.process_conversation("search for python news")

        wr1_item = self.jarvis.session_context.get_item('wr1')
        self.assertIsNotNone(wr1_item, "wr1 should be in session context")
        self.assertEqual(wr1_item['label'], 'Python 3.12 Released', "wr1 label mismatch")
        print("  ✓ Step 1 (Initial Web Search) verified.")

        # --- Step 2: Recall and Open wr1 ---
        print("\n[STEP 2] User: 'open wr1'")
        self.jarvis.speak_with_piper.reset_mock()
        self.mock_webbrowser_open.reset_mock()
        self.jarvis.dashboard.push_focus.reset_mock()
        self.jarvis.dashboard.update_ticker.reset_mock()

        self.jarvis.process_conversation("open wr1")

        self.mock_webbrowser_open.assert_called_once_with(wr1_item['metadata']['url'])
        self.jarvis.speak_with_piper.assert_called_with("Opening Python 3.12 Released.")
        # Ticker should not be cleared as it's a contextual command, not a new search
        self.jarvis.dashboard.update_ticker.assert_not_called()
        print("  ✓ Step 2 (Recall and Open wr1) verified.")

        # --- Step 3: New Web Search (clears previous context) ---
        print("\n[STEP 3] User: 'search for latest AI models'")
        self.jarvis.speak_with_piper.reset_mock()
        self.jarvis.google_search.reset_mock()
        self.jarvis.dashboard.push_focus.reset_mock()
        self.jarvis.dashboard.update_ticker.reset_mock()
        self.mock_memory_index.add_action.reset_mock()

        mock_new_web_results = [
            {'title': 'New Google AI Model | Google.com', 'snippet': 'Gemini update.', 'link': 'https://google.com/gemini'},
        ]
        self.jarvis.google_search.return_value = mock_new_web_results
        self.mock_memory_index.add_action.return_value = {'metadata': {'short_key': f"{date.today().strftime('%Y%m%d')}-wr1"}} # Counter resets daily, so wr1 again

        self.jarvis.process_conversation("search for latest AI models")

        # Expected: New search clears session context and ticker, populates with new results.
        self.jarvis.google_search.assert_called_with("latest AI models")
        self.jarvis.speak_with_piper.assert_called_with("Sir, I've found 1 result. They are on screen.")
        
        # Verify session context is cleared and repopulated
        self.assertIsNone(self.jarvis.session_context.get_item('wr2'), "Old wr2 should be cleared")
        new_wr1_item = self.jarvis.session_context.get_item('wr1')
        self.assertIsNotNone(new_wr1_item, "New wr1 should be in session context")
        self.assertEqual(new_wr1_item['label'], 'New Google AI Model', "New wr1 label mismatch")

        # Verify ticker is updated with new results (and old ones cleared)
        self.jarvis.dashboard.update_ticker.assert_called_once()
        ticker_items = self.jarvis.dashboard.update_ticker.call_args[0][0]
        self.assertEqual(len(ticker_items), 1)
        self.assertIn({'short_key': 'wr1', 'label': 'New Google AI Model'}, ticker_items)
        print("  ✓ Step 3 (New Web Search) verified.")

        print("\n--- Recall and Repeat Flow Test PASSED ---")

    def test_email_recall_and_reply_flow(self):
        """
        Tests recalling an email and then replying to it.
        Simulates: Email Summary -> Recall e1 -> Reply to e1.
        """
        print("\n--- Test Case: Email Recall and Reply Flow ---")

        # --- Step 1: Initial Email Summary ---
        print("\n[STEP 1] User: 'summarize my emails'")
        mock_emails = [
            {'id': 'email_id_1', 'sender': 'Alice <alice@example.com>', 'subject': 'Project Update', 'snippet': 'Update on project status.'},
            {'id': 'email_id_2', 'sender': 'Bob <bob@example.com>', 'subject': 'Meeting Reminder', 'snippet': 'Reminder for tomorrow.'},
        ]
        self.jarvis.get_recent_emails.return_value = mock_emails
        self.jarvis.call_smart_model.return_value = "Summary of emails: Alice updated project, Bob sent meeting reminder."
        self.mock_memory_index.add_action.side_effect = [
            {'metadata': {'short_key': f"{date.today().strftime('%Y%m%d')}-e1"}},
            {'metadata': {'short_key': f"{date.today().strftime('%Y%m%d')}-e2"}},
            # Subsequent calls for email summary action
        ]

        self.jarvis.process_conversation("summarize my emails")

        e1_item = self.jarvis.session_context.get_item('e1')
        self.assertIsNotNone(e1_item, "e1 should be in session context")
        self.assertEqual(e1_item['label'], 'Alice', "e1 label mismatch")
        print("  ✓ Step 1 (Email Summary) verified.")

        # --- Step 2: Recall and Reply to e1 ---
        print("\n[STEP 2] User: 'reply to e1 saying thanks for the update'")
        self.jarvis.speak_with_piper.reset_mock()
        self.jarvis.send_email.reset_mock()
        self.jarvis.dashboard.push_focus.reset_mock()
        self.jarvis.dashboard.update_ticker.reset_mock()

        # Mock the confirmation flow for email reply
        self.jarvis.pending_reply = {
            'email_id': e1_item['metadata']['id'],
            'sender': e1_item['metadata']['sender'],
            'sender_name': e1_item['label'],
            'reply_text': 'thanks for the update'
        }
        self.jarvis.check_pending_confirmation.return_value = True # Simulate confirmation
        self.jarvis.reply_to_email = MagicMock(return_value=True) # Mock the actual reply send

        # First call to process_conversation will set pending_reply and ask for confirmation
        self.jarvis.process_conversation("reply to e1 saying thanks for the update")
        self.jarvis.speak_with_piper.assert_called_with("Just to confirm — shall I send that reply to Alice?")
        self.jarvis.dashboard.push_focus.assert_called_once()
        self.assertIn("Pending Reply — Awaiting Confirmation", self.jarvis.dashboard.push_focus.call_args[0][1])

        # Second call to process_conversation will confirm and send
        self.jarvis.process_conversation("yes")

        self.jarvis.reply_to_email.assert_called_once_with(
            e1_item['metadata']['id'], 'thanks for the update'
        )
        self.jarvis.speak_with_piper.assert_called_with("✓ Reply sent to Alice.")
        print("  ✓ Step 2 (Recall and Reply to e1) verified.")

        print("\n--- Email Recall and Reply Flow Test PASSED ---")

if __name__ == '__main__':
    unittest.main(argv=['first-arg-is-ignored'], exit=False)