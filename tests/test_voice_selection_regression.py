"""Regression tests for generic voice command and selection handling."""

import tempfile
import unittest
from pathlib import Path

from command_engine.intent import IntentEngine
from command_engine import executor
from tools.phonetic_matcher import score_candidate
from tools.universal_resolver import UniversalResolver


class GenericVoiceSelectionTests(unittest.TestCase):

    def test_selection_with_action_suffix(self):
        engine = IntentEngine()
        cases = {
            "number 1 kholo": "1",
            "number one open": "1",
            "1 kholo": "1",
            "2 open karo": "2",
            "पहला खोलो": "1",
            "pahla kholo": "1",
            "दूसरा वाला खोलो": "2",
            "pahla": "1",
        }
        for command, expected in cases.items():
            with self.subTest(command=command):
                self.assertEqual(engine._detect_selection(command), expected)
                self.assertEqual(executor._get_selection_number(command, {}), expected)

    def test_generic_open_phrases(self):
        engine = IntentEngine()
        cases = (
            ("pik sanu kholo", "open", "pik sanu"),
            ("pik sanu kholen", "open", "pik sanu"),
            ("opan may siesasi akaunt", "open", "may siesasi akaunt"),
            ("myujik kholo", "open", "myujik"),
        )
        for command, expected_intent, expected_target in cases:
            with self.subTest(command=command):
                result = engine.detect(command)
                self.assertEqual(result["intent"], expected_intent)
                self.assertEqual(result["target"], expected_target)

    def test_phonetic_target_similarity_is_generic(self):
        self.assertGreaterEqual(score_candidate("pik sanu", "pic sanu.jpg"), 0.72)
        self.assertGreaterEqual(score_candidate("vard", "word"), 0.72)
        self.assertLess(score_candidate("pik sanu", "calculator"), 0.72)

    def test_fuzzy_duplicate_files_remain_selectable(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            left = base / "left"
            right = base / "right"
            left.mkdir()
            right.mkdir()
            first = left / "Project Notes.txt"
            second = right / "Project Notes.txt"
            first.write_text("one", encoding="utf-8")
            second.write_text("two", encoding="utf-8")

            resolver = UniversalResolver()
            resolver.common_paths = [str(base)]
            resolver.start_menu_paths = []
            resolver.desktop_paths = []
            resolver.max_results = 20

            results = resolver._fuzzy_search_known_locations("project ntes")
            self.assertIn(str(first), results)
            self.assertIn(str(second), results)
            self.assertEqual(len([p for p in results if p.endswith("Project Notes.txt")]), 2)


if __name__ == "__main__":
    unittest.main()
