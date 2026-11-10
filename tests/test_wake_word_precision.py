"""Wake-word confidence regressions from recorded Windows logs."""

from voice.speech_to_text import SpeechToText
from voice.voice_controller import VoiceController


def make_stt():
    stt = SpeechToText.__new__(SpeechToText)
    stt._log = lambda _message: None
    stt._last_raw_text = ""
    stt._last_text = ""
    stt._last_language = ""
    stt._last_status = ""
    return stt


def test_canonical_vyom_wake_word_still_matches():
    stt = make_stt()
    matched, alias = stt._wake_detected("Vyom")

    assert matched is True
    assert alias == "vyom"


def test_common_near_match_words_do_not_wake_vyom():
    stt = make_stt()

    assert stt._wake_detected("Vivo")[0] is False
    assert stt._wake_detected("Jio")[0] is False
    assert stt._wake_detected("young")[0] is False
    assert stt._wake_detected("viom", allow_fuzzy=False, strict=True)[0] is False


def test_lower_ranked_fuzzy_alternative_does_not_override_primary_transcript():
    stt = make_stt()
    stt._recognize_one = lambda *_args, **_kwargs: {
        "status": "recognized",
        "success": True,
        "text": "Vivo",
        "raw_text": "Vivo",
        "alternatives": ["Vivo", "viom"],
        "language": "en-IN",
    }

    result = stt._recognize_wake(object())

    assert result["status"] == "wake_not_detected"
    assert result["success"] is False


def test_voice_controller_does_not_fuzzily_activate_from_vivo():
    controller = VoiceController.__new__(VoiceController)
    controller.wake_words = (
        "hey vyom", "हे व्योम", "vyom ji", "व्योम जी",
        "vyom", "व्योम", "viyom", "viom", "वियोम", "वियम",
        "vyam", "veom", "vyoam", "viyam", "biom", "beyom", "vyoum",
    )
    assert controller._find_wake_word("Vivo") is None
    assert controller._find_wake_word("Vyom") == "vyom"
