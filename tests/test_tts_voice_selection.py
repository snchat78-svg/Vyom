from types import SimpleNamespace

from voice.text_to_speech import TextToSpeech


class FakeEngine:
    def __init__(self, voices):
        self.voices = voices
        self.selected = None

    def getProperty(self, name):
        return self.voices if name == "voices" else None

    def setProperty(self, name, value):
        if name == "voice":
            self.selected = value


def make_voice(voice_id, name, languages):
    return SimpleNamespace(id=voice_id, name=name, languages=languages)


def test_hindi_text_prefers_installed_hindi_voice():
    tts = TextToSpeech.__new__(TextToSpeech)
    tts.debug = False
    tts._log = lambda _message: None
    hindi = make_voice("hi-IN", "Hindi Voice", ["hi-IN"])
    david = make_voice("en-US", "Microsoft David Desktop", ["en-US"])
    engine = FakeEngine([david, hindi])

    tts._select_voice_on_engine(engine, "भारत की राजधानी नई दिल्ली है।")

    assert engine.selected == "hi-IN"


def test_hindi_text_prefers_indian_english_over_us_english_when_hindi_is_absent():
    tts = TextToSpeech.__new__(TextToSpeech)
    tts.debug = False
    tts._log = lambda _message: None
    david = make_voice("en-US", "Microsoft David Desktop", ["en-US"])
    indian = make_voice("en-IN", "Indian English Voice", ["en-IN"])
    engine = FakeEngine([david, indian])

    tts._select_voice_on_engine(engine, "भारत की राजधानी नई दिल्ली है।")

    assert engine.selected == "en-IN"
