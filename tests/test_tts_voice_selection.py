undefined

def test_windows_hindi_wav_helper_plays_rendered_wav_and_removes_temp_file(monkeypatch):
    import sys
    import subprocess
    import os
    from types import SimpleNamespace

    played = []
    def play(path, flags):
        with open(path, "rb") as audio_file:
            signature = audio_file.read(4)
        played.append((path, flags, signature))
    fake_winsound = SimpleNamespace(SND_FILENAME=1, SND_SYNC=2, PlaySound=play)
    monkeypatch.setitem(sys.modules, "winsound", fake_winsound)

    calls = []
    def fake_run(command, **kwargs):
        calls.append((command, kwargs))
        return SimpleNamespace(stdout=b"RIFF" + b"0000" + b"WAVE" + b"audio-sample" * 4)
    monkeypatch.setattr(subprocess, "run", fake_run)

    tts = TextToSpeech.__new__(TextToSpeech)
    tts.debug = False
    tts._log = lambda _message: None
    result = tts._speak_with_espeak_wav("espeak-ng.exe", "भारत की राजधानी नई दिल्ली है।")

    assert result["success"] is True
    assert calls[0][0][1:4] == ["-v", "hi", "--stdout"]
    assert played and played[0][1] == 3 and played[0][2] == b"RIFF"
    assert not os.path.exists(played[0][0])


def test_windows_hindi_wav_helper_rejects_invalid_audio_stream(monkeypatch):
    import sys
    import subprocess
    from types import SimpleNamespace

    monkeypatch.setitem(sys.modules, "winsound", SimpleNamespace(SND_FILENAME=1, SND_SYNC=2, PlaySound=lambda *_: None))
    monkeypatch.setattr(subprocess, "run", lambda *_args, **_kwargs: SimpleNamespace(stdout=b"not-a-wave"))
    tts = TextToSpeech.__new__(TextToSpeech)
    tts.debug = False
    tts._log = lambda _message: None
    result = tts._speak_with_espeak_wav("espeak-ng.exe", "नमस्ते")
    assert result["success"] is False
    assert "RuntimeError" in result["message"]
