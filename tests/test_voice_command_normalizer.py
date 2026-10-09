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

    def test_low_similarity_word_is_not_forced_into_command(self):
        normalizer = VoiceCommandNormalizer(min_similarity=0.80)
        result = normalizer.normalize("cloze myfile")
        self.assertEqual(result["text"], "close myfile")


if __name__ == "__main__":
    unittest.main()
