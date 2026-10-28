import os
import sys
import tempfile
import unittest
from pathlib import Path

# Add project root
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.memory import JarvisMemoryManager
from core.memory_parser import MemoryCommandParser
from core.brain import JarvisBrain

class TestJarvisPersistentMemory(unittest.TestCase):
    def setUp(self):
        # Create an isolated temporary SQLite database for clean test runs
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "test_memory.db"
        self.config = {
            "memory_db_path": str(self.db_path),
            "prefix_saved_answer": False
        }
        self.brain = JarvisBrain(config=self.config)

    def tearDown(self):
        try:
            self.temp_dir.cleanup()
        except Exception:
            pass

    # -------------------------------------------------------------
    # 1. Save New Question-Answer Pair & Verify Persistence
    # -------------------------------------------------------------
    def test_01_save_new_memory(self):
        cmd = "Jarvis, remember this: If I ask who is my best friend, answer Rahul."
        response = self.brain.process_command(cmd)

        self.assertIn("Done, boss. I've saved this:", response)
        self.assertIn("Question: who is my best friend", response)
        self.assertIn("Answer: Rahul", response)

        # Verify directly in SQLite DB
        count = self.brain.memory_mgr.get_memory_count()
        self.assertEqual(count, 1)

    # -------------------------------------------------------------
    # 2. Retrieve Exact Saved Answer (Exact Answer Mode)
    # -------------------------------------------------------------
    def test_02_retrieve_exact_saved_answer(self):
        self.brain.memory_mgr.save_memory("Who is my best friend?", "Rahul")
        ans = self.brain.process_command("Who is my best friend?")
        # Exact answer mode: must return stored answer as written, no sarcasm or AI tampering
        self.assertEqual(ans.strip(), "Rahul")

    # -------------------------------------------------------------
    # 3. Retrieve Answer After Restarting JARVIS (Survives Restarts)
    # -------------------------------------------------------------
    def test_03_restart_persistence(self):
        # Save in first instance
        self.brain.memory_mgr.save_memory("Who is my best friend?", "Rahul")

        # Simulate full application restart by destroying the brain and creating a fresh instance
        del self.brain
        restarted_brain = JarvisBrain(config=self.config)

        # Verify it still answers accurately from disk
        ans_en = restarted_brain.process_command("Who is my best friend?")
        self.assertEqual(ans_en.strip(), "Rahul")

        ans_hi = restarted_brain.process_command("Mera best friend kaun hai?")
        self.assertEqual(ans_hi.strip(), "Rahul")

    # -------------------------------------------------------------
    # 4. Multilingual Matching (English, Hindi, Hinglish, Slang)
    # -------------------------------------------------------------
    def test_04_multilingual_matching(self):
        self.brain.memory_mgr.save_memory("Who is my best friend?", "Rahul")

        test_variations = [
            "Who is my best friend?",
            "Jarvis, tell me who my best friend is.",
            "Mera best friend kaun hai?",
            "Who is my bestie?",
            "Suno Jarvis, mera pakka dost kaun hai?",
            "Mera jigri dost kaun hai?"
        ]

        for q in test_variations:
            with self.subTest(query=q):
                resp = self.brain.process_command(q)
                self.assertEqual(resp.strip(), "Rahul", f"Failed to match query: '{q}'")

    # -------------------------------------------------------------
    # 5. Avoid Incorrect Matches for Unrelated Questions
    # -------------------------------------------------------------
    def test_05_avoid_incorrect_matches(self):
        self.brain.memory_mgr.save_memory("Who is my best friend?", "Rahul")

        unrelated_queries = [
            "Who is the prime minister of India?",
            "What is today's date?",
            "Decrease screen brightness",
            "Mute the system volume",
            "What is Python programming language?"
        ]

        for q in unrelated_queries:
            with self.subTest(query=q):
                resp = self.brain.process_command(q)
                self.assertNotEqual(resp.strip(), "Rahul", f"Unrelated query '{q}' falsely matched custom memory!")

    # -------------------------------------------------------------
    # 6. Natural Voice Teaching Patterns
    # -------------------------------------------------------------
    def test_06_natural_voice_teaching_patterns(self):
        # Pattern A: "Jarvis, is question ka answer yaad rakhna: What is my favourite colour? Blue."
        r1 = self.brain.process_command("Jarvis, is question ka answer yaad rakhna: What is my favourite colour? Blue.")
        self.assertIn("Done, boss. I've saved this:", r1)
        self.assertEqual(self.brain.process_command("What is my favourite colour?").strip(), "Blue")
        self.assertEqual(self.brain.process_command("Mera pasandida rang kya hai?").strip(), "Blue")

        # Pattern B: "Remember this answer permanently: My college name is MMMUT Gorakhpur."
        r2 = self.brain.process_command("Remember this answer permanently: My college name is MMMUT Gorakhpur.")
        self.assertIn("Done, boss. I've saved this:", r2)
        self.assertEqual(self.brain.process_command("What is my college name?").strip(), "MMMUT Gorakhpur")
        self.assertEqual(self.brain.process_command("Mere college ka naam kya hai?").strip(), "MMMUT Gorakhpur")

        # Pattern C: "Jarvis, save this in your memory. Question: What is my project name? Answer: Nova."
        r3 = self.brain.process_command("Jarvis, save this in your memory. Question: What is my project name? Answer: Nova.")
        self.assertIn("Done, boss. I've saved this:", r3)
        self.assertEqual(self.brain.process_command("What is my project name?").strip(), "Nova")
        self.assertEqual(self.brain.process_command("Mera project name kya hai?").strip(), "Nova")

        # Pattern D: "Whenever I ask who is my best friend, always reply Rahul."
        r4 = self.brain.process_command("Whenever I ask who is my mentor, always reply Dr. APJ Abdul Kalam.")
        self.assertIn("Done, boss. I've saved this:", r4)
        self.assertEqual(self.brain.process_command("Who is my mentor?").strip(), "Dr. APJ Abdul Kalam")

    # -------------------------------------------------------------
    # 7. Duplicate Handling & Confirmation Flow
    # -------------------------------------------------------------
    def test_07_duplicate_handling_and_confirmation(self):
        # Save initial
        self.brain.process_command("Whenever I ask who is my best friend, always reply Rahul.")

        # Try to save again with different answer -> asks confirmation
        r_dup = self.brain.process_command("Whenever I ask who is my best friend, always reply Amit.")
        self.assertIn("already saved", r_dup)
        self.assertIn("Do you want to update it to 'Amit'?", r_dup)

        # Confirm update
        r_conf = self.brain.process_command("Yes confirm")
        self.assertIn("updated the answer", r_conf)

        # Verify updated answer
        self.assertEqual(self.brain.process_command("Who is my best friend?").strip(), "Amit")

    # -------------------------------------------------------------
    # 8. Update Voice Command
    # -------------------------------------------------------------
    def test_08_update_voice_command(self):
        self.brain.memory_mgr.save_memory("Who is my best friend?", "Rahul")

        r_upd = self.brain.process_command("Jarvis, update the answer to my best-friend question to Amit.")
        self.assertIn("Are you sure you want to replace it with 'Amit'?", r_upd)

        r_conf = self.brain.process_command("Haan replace kar do")
        self.assertIn("updated the answer", r_conf)
        self.assertEqual(self.brain.process_command("Who is my best friend?").strip(), "Amit")

    # -------------------------------------------------------------
    # 9. Delete Voice Command & Confirmation
    # -------------------------------------------------------------
    def test_09_delete_voice_command(self):
        self.brain.memory_mgr.save_memory("Who is my best friend?", "Rahul")
        self.assertEqual(self.brain.memory_mgr.get_memory_count(), 1)

        r_del = self.brain.process_command("Jarvis, forget the saved answer to who is my best friend.")
        self.assertIn("are you sure you want to delete", r_del.lower())

        r_conf = self.brain.process_command("Yes delete")
        self.assertIn("deleted the saved memory", r_conf)

        # Verify memory is gone
        self.assertEqual(self.brain.memory_mgr.get_memory_count(), 0)

    # -------------------------------------------------------------
    # 10. List Saved Memories Voice Command
    # -------------------------------------------------------------
    def test_10_list_memories(self):
        self.brain.memory_mgr.save_memory("Who is my best friend?", "Rahul")
        self.brain.memory_mgr.save_memory("What is my project name?", "Nova")

        r_list = self.brain.process_command("Jarvis, show all my saved questions.")
        self.assertIn("saved memories", r_list)
        self.assertIn("best friend", r_list)
        self.assertIn("project name", r_list)

    # -------------------------------------------------------------
    # 11. Search / Retrieve Memory Voice Command
    # -------------------------------------------------------------
    def test_11_search_retrieve_memory(self):
        self.brain.memory_mgr.save_memory("What is my college name?", "MMMUT Gorakhpur")

        r_search = self.brain.process_command("Jarvis, search my memory for the answer about college.")
        self.assertIn("MMMUT Gorakhpur", r_search)

    # -------------------------------------------------------------
    # 12. Backup Export & Import Verification
    # -------------------------------------------------------------
    def test_12_backup_export_import(self):
        self.brain.memory_mgr.save_memory("Q1", "A1")
        self.brain.memory_mgr.save_memory("Q2", "A2")

        export_path = str(Path(self.temp_dir.name) / "backup_test.json")
        ok, p = self.brain.memory_mgr.export_backup(export_path)
        self.assertTrue(ok)
        self.assertTrue(Path(p).exists())

        # Clear active memories
        all_m = self.brain.memory_mgr.list_all_memories()
        for m in all_m:
            self.brain.memory_mgr.delete_memory(m["id"], hard_delete=True)
        self.assertEqual(self.brain.memory_mgr.get_memory_count(), 0)

        # Import from backup
        ok_imp, count, msg = self.brain.memory_mgr.import_backup(export_path)
        self.assertTrue(ok_imp)
        self.assertEqual(count, 2)
        self.assertEqual(self.brain.memory_mgr.get_memory_count(), 2)

    # -------------------------------------------------------------
    # 13. Detailed Multi-sentence / Hinglish Paragraph Preservation
    # -------------------------------------------------------------
    def test_13_exact_paragraph_preservation(self):
        detailed_ans = "Mera college MMMUT Gorakhpur hai jo 1962 me establish hua tha, aur yahan ki CS branch top rankers ki choice hai."
        self.brain.memory_mgr.save_memory("College details batao", detailed_ans)

        ans = self.brain.process_command("College details batao")
        # Byte-for-byte exact equality
        self.assertEqual(ans.strip(), detailed_ans)

if __name__ == "__main__":
    unittest.main()
