import unittest

from command_engine.intent import IntentEngine


class SemanticDictionContractTests(unittest.TestCase):
    """Different surface wording should preserve the same supported intent."""

    def setUp(self):
        self.engine = IntentEngine()

    def assert_action(self, utterance, expected_intent, expected_target):
        result = self.engine.detect(utterance)
        self.assertEqual(
            result["intent"],
            expected_intent,
            msg=f"Unexpected interpretation for: {utterance!r}",
        )
        self.assertEqual(
            result.get("target", "").casefold(),
            expected_target.casefold(),
            msg=f"Target changed for: {utterance!r}",
        )

    def test_open_request_survives_polite_and_multilingual_diction(self):
        cases = (
            "open Notepad",
            "please open Notepad",
            "could you open Notepad?",
            "would you please launch Notepad for me?",
            "Hey Vyom, could you please launch Notepad for me?",
            "mujhe Notepad khol do",
            "zara Notepad kholo",
            "Notepad ko kholo",
            "Notepad open kar do",
            "Notepad को खोलो",
        )
        for utterance in cases:
            with self.subTest(utterance=utterance):
                self.assert_action(utterance, "open", "notepad")

    def test_close_request_survives_polite_and_multilingual_diction(self):
        cases = (
            "close Notepad",
            "please close Notepad",
            "could you please close Notepad?",
            "Notepad band kar do",
            "Notepad ko band kar do",
            "Notepad बंद कर दो",
            "कृपया Notepad बंद कर दो",
        )
        for utterance in cases:
            with self.subTest(utterance=utterance):
                self.assert_action(utterance, "close_app", "notepad")

    def test_dynamic_target_and_extension_are_preserved(self):
        self.assert_action(
            "Hey Vyom, could you open my-project.v2 for me?",
            "open",
            "my-project.v2",
        )

    def test_politeness_without_a_supported_action_does_not_invent_one(self):
        result = self.engine.detect("Could you help me with this?")
        self.assertNotIn(result["intent"], {"open", "close_app"})

    def test_typed_payload_is_not_reinterpreted_as_an_open_command(self):
        result = self.engine.detect("type please open this sentence")
        self.assertNotEqual(result["intent"], "open")


if __name__ == "__main__":
    unittest.main()
