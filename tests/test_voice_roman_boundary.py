import unittest

from voice.romanizer import RomanTextNormalizer, normalize_voice_text
from voice.voice_controller import VoiceController


class FakeSpeechToText:
    error_message = ""

    def is_available(self):
        return True

    def listen(self, **kwargs):
        return {
            "success": True,
            "status": "recognized",
            "text": "स्काइप खोलो",
            "language": "hi-IN",
        }


class FakeTextToSpeech:
    def is_available(self):
        return True

    def speak(self, text):
        return {"success": True}

    def stop(self):
        return None


class FakeConversationManager:
    def __init__(self):
        self.messages = []

    def process_voice(self, text):
        self.messages.append(text)
        return {"success": True, "message": "Done", "status": "success"}


class RomanVoiceBoundaryTests(unittest.TestCase):
    def test_romanizer_converts_devanagari_to_latin(self):
        value = normalize_voice_text("स्काइप खोलो")
        self.assertEqual(value, "skaip kholo")
        self.assertFalse(RomanTextNormalizer.contains_devanagari(value))

    def test_romanizer_preserves_english_input(self):
        value = normalize_voice_text("Skype kholo")
        self.assertEqual(value, "Skype kholo")
        self.assertFalse(RomanTextNormalizer.contains_devanagari(value))

    def test_romanizer_handles_mixed_command_without_devanagari(self):
        value = normalize_voice_text("Google Chrome खोलो")
        self.assertEqual(value, "Google Chrome kholo")
        self.assertFalse(RomanTextNormalizer.contains_devanagari(value))

    def test_voice_controller_normalizes_stt_before_executor(self):
        manager = FakeConversationManager()
        controller = VoiceController(
            stt=FakeSpeechToText(),
            tts=FakeTextToSpeech(),
            conversation_manager=manager,
        )

        result = controller.listen_once(
            announce=False,
            timeout=1,
            phrase_time_limit=1,
            wake_mode=False,
        )

        self.assertEqual(result["raw_text"], "स्काइप खोलो")
        self.assertEqual(result["text"], "skaip kholo")
        self.assertFalse(RomanTextNormalizer.contains_devanagari(result["text"]))

        controller.process_text(result["text"])
        self.assertEqual(manager.messages, ["skaip kholo"])


if __name__ == "__main__":
    unittest.main()
