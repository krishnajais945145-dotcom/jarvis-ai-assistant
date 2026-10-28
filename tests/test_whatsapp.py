import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from core.whatsapp_parser import WhatsAppCommandParser
from automation.whatsapp_files import resolve_whatsapp_file, APPROVED_SEARCH_DIRS
from automation.whatsapp_automation import (
    WhatsAppAutomation,
    STATUS_DISCONNECTED,
    STATUS_CONNECTED,
    STATUS_AWAITING_QR,
    STATUS_AWAITING_CONFIRMATION,
    STATUS_SUCCESS
)
from core.brain import JarvisBrain

class TestWhatsAppAutomation(unittest.TestCase):

    def setUp(self):
        self.brain = JarvisBrain()
        # Mock LLM to avoid external API calls during testing
        self.brain.llm_client = None

    # -------------------------------------------------------------------------
    # 1. Natural Voice Command Parsing (Hindi, Hinglish, English)
    # -------------------------------------------------------------------------
    def test_open_commands_parsing(self):
        open_samples = [
            "Hey Jarvis, WhatsApp kholo.",
            "Jarvis, WhatsApp Web open kar do.",
            "Jarvis, WhatsApp pe message bhejna hai.",
            "open whatsapp web",
            "WhatsApp kholo"
        ]
        for cmd in open_samples:
            parsed = WhatsAppCommandParser.parse(cmd)
            self.assertIsNotNone(parsed, f"Failed to parse open command: {cmd}")
            self.assertEqual(parsed["action"], "open_whatsapp", f"Wrong action for: {cmd}")

    def test_text_message_commands_parsing(self):
        samples = [
            ("Jarvis, Rahul ko WhatsApp pe message bhejo: Main 10 minute mein aa raha hoon.", "Rahul", "Main 10 minute mein aa raha hoon."),
            ("WhatsApp pe Neha ko likho ki kal college nahi aaunga.", "Neha", "kal college nahi aaunga."),
            ("Rahul ko WhatsApp pe message bhejo Main 10 minute mein aa raha hoon", "Rahul", "Main 10 minute mein aa raha hoon")
        ]
        for cmd, expected_rec, expected_msg in samples:
            parsed = WhatsAppCommandParser.parse(cmd)
            self.assertIsNotNone(parsed, f"Failed to parse text command: {cmd}")
            self.assertEqual(parsed["action"], "send_text")
            self.assertEqual(parsed["recipient"], expected_rec)
            self.assertIn(expected_msg.strip("."), parsed["message"])

    def test_pdf_commands_parsing(self):
        samples = [
            ("Priya ko ye PDF WhatsApp kar do.", "Priya", "latest.pdf", None),
            ("Downloads folder se assignment.pdf Amit ko bhej do.", "Amit", "assignment.pdf", "downloads"),
            ("Jarvis, Downloads folder se report.pdf Rahul ko WhatsApp kar do.", "Rahul", "report.pdf", "downloads")
        ]
        for cmd, exp_rec, exp_file, exp_folder in samples:
            parsed = WhatsAppCommandParser.parse(cmd)
            self.assertIsNotNone(parsed, f"Failed to parse PDF command: {cmd}")
            self.assertEqual(parsed["action"], "send_pdf")
            self.assertEqual(parsed["recipient"], exp_rec)
            self.assertEqual(parsed["filename"], exp_file)
            self.assertEqual(parsed["folder_hint"], exp_folder)

    def test_image_commands_parsing(self):
        samples = [
            ("Desktop wali photo Rahul ko send kar do.", "Rahul", "latest_image.png", "desktop"),
            ("Jarvis, Desktop se meri photo Rahul ko bhej do.", "Rahul", "meri_photo.png", "desktop"),
            ("Downloads wali image Priya ko WhatsApp kar do.", "Priya", "latest_image.png", "downloads"),
            ("Is screenshot ko Amit ko send kar do.", "Amit", "screenshot.png", None)
        ]
        for cmd, exp_rec, exp_file, exp_folder in samples:
            parsed = WhatsAppCommandParser.parse(cmd)
            self.assertIsNotNone(parsed, f"Failed to parse Image command: {cmd}")
            self.assertEqual(parsed["action"], "send_image")
            self.assertEqual(parsed["recipient"], exp_rec)
            self.assertEqual(parsed["filename"], exp_file)
            self.assertEqual(parsed["folder_hint"], exp_folder)

    def test_cancel_commands_parsing(self):
        samples = [
            "Cancel WhatsApp message",
            "WhatsApp message cancel karo",
            "Mat bhejo",
            "Ruk jao WhatsApp mat bhejo"
        ]
        for cmd in samples:
            parsed = WhatsAppCommandParser.parse(cmd)
            self.assertIsNotNone(parsed, f"Failed to parse cancel command: {cmd}")
            self.assertEqual(parsed["action"], "cancel")

    # -------------------------------------------------------------------------
    # 2. File Verification & Search in Approved Folders
    # -------------------------------------------------------------------------
    def test_file_resolution_valid_and_missing(self):
        # Create a harmless temporary PDF in Downloads or Documents
        test_dir = APPROVED_SEARCH_DIRS["downloads"]
        test_dir.mkdir(parents=True, exist_ok=True)
        test_pdf = test_dir / "jarvis_unit_test_doc.pdf"
        try:
            with open(test_pdf, "w") as f:
                f.write("%PDF-1.4 test document content")

            # 1. Search existing file
            ok, msg, files = resolve_whatsapp_file("jarvis_unit_test_doc.pdf", folder_hint="downloads", file_type="pdf")
            self.assertTrue(ok)
            self.assertEqual(len(files), 1)
            self.assertEqual(files[0].name, "jarvis_unit_test_doc.pdf")

            # 2. Search missing file
            ok_m, msg_m, files_m = resolve_whatsapp_file("non_existent_random_doc_12345.pdf", file_type="pdf")
            self.assertFalse(ok_m)
            self.assertEqual(len(files_m), 0)
            self.assertIn("nahi mila", msg_m)
        finally:
            if test_pdf.exists():
                test_pdf.unlink()

    # -------------------------------------------------------------------------
    # 3. Confirmation and Cancellation Workflows
    # -------------------------------------------------------------------------
    def test_explicit_confirmation_required_before_sending(self):
        # Setup pending confirmation in brain
        self.brain.pending_whatsapp_confirmation = {
            "type": "text",
            "recipient": "Rahul",
            "message": "Main 10 min me aa raha hoon"
        }

        # Mock send_confirmed_action to return success
        self.brain.whatsapp_mgr.send_confirmed_action = MagicMock(return_value=(True, "Message delivered to Rahul"))

        # User confirms with 'Haan bhejo'
        reply = self.brain.process_command("Haan bhejo")
        self.assertIn("Message delivered to Rahul", reply)
        self.assertIsNone(self.brain.pending_whatsapp_confirmation)
        self.brain.whatsapp_mgr.send_confirmed_action.assert_called_once()

    def test_cancellation_flow(self):
        self.brain.pending_whatsapp_confirmation = {
            "type": "file",
            "recipient": "Amit",
            "filename": "assignment.pdf"
        }
        self.brain.whatsapp_mgr.cancel_pending = MagicMock(return_value=(True, "Cancelled"))

        # User cancels
        reply = self.brain.process_command("Mat bhejo cancel kar do")
        self.assertTrue(any(w in reply.lower() for w in ["cancel", "safe", "abort"]))
        self.assertIsNone(self.brain.pending_whatsapp_confirmation)
        self.brain.whatsapp_mgr.cancel_pending.assert_called_once()

    # -------------------------------------------------------------------------
    # 4. Contact Disambiguation Flow
    # -------------------------------------------------------------------------
    def test_ambiguous_contact_selection(self):
        # Simulate multiple contacts found
        self.brain.pending_whatsapp_contact_choice = {
            "contacts": ["Rahul Sharma", "Rahul College", "Rahul Gym"],
            "pending_action": "send_text",
            "message": "Kal class hai kya?"
        }
        self.brain.whatsapp_mgr.prepare_text_message = MagicMock(return_value=(True, "Prepared"))

        # User says "Pehla wala"
        reply = self.brain.process_command("Pehla wala Rahul")
        self.assertIn("Rahul Sharma", reply)
        self.assertIn("Kya main send kar doon?", reply)
        self.assertIsNotNone(self.brain.pending_whatsapp_confirmation)
        self.assertEqual(self.brain.pending_whatsapp_confirmation["recipient"], "Rahul Sharma")

    # -------------------------------------------------------------------------
    # 5. File Disambiguation Flow
    # -------------------------------------------------------------------------
    def test_ambiguous_file_selection(self):
        f1 = Path("C:/Users/test/Downloads/report_v1.pdf")
        f2 = Path("C:/Users/test/Downloads/report_final.pdf")

        self.brain.pending_whatsapp_file_choice = {
            "files": [f1, f2],
            "recipient": "Neha",
            "attachment_type": "pdf"
        }
        self.brain.whatsapp_mgr.search_and_select_contact = MagicMock(return_value=(True, "Selected", ["Neha"]))
        self.brain.whatsapp_mgr.prepare_file_attachment = MagicMock(return_value=(True, "Attached"))

        # User selects "Number 2"
        reply = self.brain.process_command("Number 2")
        self.assertIn("report_final.pdf", reply)
        self.assertIn("Kya main send kar doon?", reply)
        self.assertIsNotNone(self.brain.pending_whatsapp_confirmation)
        self.assertEqual(self.brain.pending_whatsapp_confirmation["filename"], "report_final.pdf")

    # -------------------------------------------------------------------------
    # 6. Session Status & QR Code Detection
    # -------------------------------------------------------------------------
    def test_status_when_qr_code_needed(self):
        with patch.object(self.brain.whatsapp_mgr, "check_status", return_value=(STATUS_AWAITING_QR, "Scan QR")):
            reply = self.brain.process_command("Rahul ko WhatsApp pe message bhejo: Hi")
            self.assertIn("QR code scan", reply)

    def test_status_when_browser_disconnected(self):
        with patch.object(self.brain.whatsapp_mgr, "check_status", return_value=(STATUS_DISCONNECTED, "Offline")):
            with patch.object(self.brain.whatsapp_mgr, "open_whatsapp_web", return_value=(False, "Chrome not found")):
                reply = self.brain.process_command("Rahul ko WhatsApp pe message bhejo: Hi")
                self.assertIn("WhatsApp Web open nahi ho paya", reply)

    # -------------------------------------------------------------------------
    # 7. Typo Tolerance and Natural English Commands
    # -------------------------------------------------------------------------
    def test_typo_tolerant_image_command(self):
        cmd = "sendd the image on my whasstap web to tulsi which is on my desk top"
        parsed = WhatsAppCommandParser.parse(cmd)
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed["action"], "send_image")
        self.assertEqual(parsed["recipient"], "tulsi")
        self.assertEqual(parsed["folder_hint"], "desktop")

if __name__ == "__main__":
    unittest.main()
