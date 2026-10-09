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


def test_local_espeak_fallback_uses_hindi_voice(monkeypatch):
    import subprocess

    tts = TextToSpeech.__new__(TextToSpeech)
    tts.debug = False
    tts._log = lambda _message: None
    tts._find_espeak_ng = lambda: r"C:\\Tools\\espeak-ng.exe"
    calls = []

    def fake_run(command, **kwargs):
        calls.append((command, kwargs))
        return None

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = tts._speak_with_espeak("भारत की राजधानी नई दिल्ली है।")

    assert result["success"] is True
    assert calls[0][0][1:3] == ["-v", "hi"]
    assert calls[0][0][-1] == "भारत की राजधानी नई दिल्ली है।"



class FakeSpeechEngine(FakeEngine):
    def __init__(self, voices):
        super().__init__(voices)
        self.spoken = []
        self.stopped = False

    def say(self, text):
        self.spoken.append(text)

    def runAndWait(self):
        return None

    def stop(self):
        self.stopped = True


def _make_speak_tts(mode, engine, local_speech):
    tts = TextToSpeech.__new__(TextToSpeech)
    tts.debug = False
    tts._log = lambda _message: None
    tts.tts_mode = mode
    tts.available = True
    tts.error_message = ""
    tts.engine = engine
    tts._current_voice = None
    tts.rate = 165
    tts.volume = 1.0
    tts._create_fresh_engine = lambda: engine
    tts._has_hindi_sapi_voice = lambda _engine=None: False
    tts._speak_with_espeak = local_speech
    return tts


def test_default_mode_keeps_system_selected_voice_and_does_not_require_hindi_tts():
    import os

    david = make_voice("en-US", "Microsoft David Desktop", ["en-US"])
    engine = FakeSpeechEngine([david])
    tts = _make_speak_tts(
        "system",
        engine,
        lambda _text: (_ for _ in ()).throw(AssertionError("eSpeak must be opt-in")),
    )

    result = tts.speak("भारत की राजधानी नई दिल्ली है।")

    assert result["success"] is True
    assert engine.spoken == ["भारत की राजधानी नई दिल्ली है।"]
    assert engine.selected is None
    assert os.environ.get("VYOM_TTS_MODE", "system").lower() != "force-hindi"


def test_optional_espeak_failure_falls_back_to_system_voice_without_stopping_vyom():
    david = make_voice("en-US", "Microsoft David Desktop", ["en-US"])
    engine = FakeSpeechEngine([david])
    attempts = []
    tts = _make_speak_tts(
        "espeak-ng",
        engine,
        lambda text: attempts.append(text) or {
            "success": False,
            "text": text,
            "message": "eSpeak NG not found",
        },
    )

    result = tts.speak("नमस्ते, मैं व्योम हूँ।")

    assert attempts == ["नमस्ते, मैं व्योम हूँ।"]
    assert result["success"] is True
    assert engine.spoken == ["नमस्ते, मैं व्योम हूँ।"]
    assert engine.selected is None
