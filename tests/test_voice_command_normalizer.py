import unittest

from command_engine.intent import IntentEngine
from voice.command_normalizer import VoiceCommandNormalizer


class VoiceCommandNormalizationTests(unittest.TestCase):
    def test_common_stt_errors_are_corrected_without_target_dictionary(self):
        normalizer = VoiceCommandNormalizer()
        result = normalizer.normalize("kloj notapaid")
        self.assertEqual(result["text"], "close notapaid")
        self.assertGreaterEqual(result["confidence"], 0.74)

    def test_open_and_type_corrections(self):
        normalizer = VoiceCommandNormalizer()
        result = normalizer.normalize("opan notapaid")
        self.assertEqual(result["text"], "open notapaid")

    def test_unknown_target_is_preserved(self):
        normalizer = VoiceCommandNormalizer()
        result = normalizer.normalize("kloj my-custom-file")
        self.assertEqual(result["text"], "close my-custom-file")

    def test_intent_engine_uses_corrected_command_words(self):
        engine = IntentEngine()
        result = engine.detect("kloj notapaid")
        self.assertEqual(result["intent"], "close_app")
        self.assertEqual(result["target"], "notapaid")
        self.assertEqual(result["voice"]["text"], "close notapaid")

    def test_normalizer_does_not_rewrite_hindi_to_find(self):
        normalizer = VoiceCommandNormalizer()
        result = normalizer.normalize("hindi men bat karo")
        self.assertEqual(result["text"], "hindi men bat karo")



    def test_target_and_user_payload_are_not_rewritten_as_hindi_actions(self):
        normalizer = VoiceCommandNormalizer()
        cases = {
            "type khol": "type khol",
            "write kholo": "write kholo",
            "search khol": "search khol",
            "open khol": "open khol",
            "close band": "close band",
            "this is khol text": "this is khol text",
        }
        for source, expected in cases.items():
            with self.subTest(source=source):
                result = normalizer.normalize(source)
                self.assertEqual(result["text"], expected)
                self.assertFalse(
                    any(correction["from"] in {"khol", "kholo", "band"}
                        for correction in result["corrections"])
                )

    def test_compound_payload_stays_intact_while_next_command_is_normalized(self):
        normalizer = VoiceCommandNormalizer()
        result = normalizer.normalize("type khol and opan notapaid")

        self.assertEqual(result["text"], "type khol and open notapaid")
        self.assertTrue(any(
            correction["from"] == "opan" and correction["to"] == "open"
            for correction in result["corrections"]
        ))
        self.assertFalse(any(
            correction["from"] == "khol"
            for correction in result["corrections"]
        ))

    def test_trailing_hindi_operation_is_still_normalized(self):
        normalizer = VoiceCommandNormalizer()
        result = normalizer.normalize("notepad kholo")

        self.assertEqual(result["text"], "notepad open")
        self.assertEqual(result["corrections"][0]["from"], "kholo")

    def test_unknown_target_from_prior_turn_does_not_become_a_learned_alias(self):
        normalizer = VoiceCommandNormalizer()

        first = normalizer.normalize("open calclulator")
        second = normalizer.normalize("calclulator")

        self.assertEqual(first["text"], "open calclulator")
        self.assertEqual(second["text"], "calclulator")
        self.assertEqual(second["corrections"], [])

    def test_low_similarity_word_is_not_forced_into_command(self):
        normalizer = VoiceCommandNormalizer(min_similarity=0.80)
        result = normalizer.normalize("cloze myfile")
        self.assertEqual(result["text"], "close myfile")


if __name__ == "__main__":
    unittest.main()
