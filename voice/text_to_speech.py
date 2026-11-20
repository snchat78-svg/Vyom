"""
Project : Vyom AI
Version : 0.2
Module  : Text To Speech

Purpose:
    Convert Vyom response text into spoken audio.

Windows 8 Friendly:
    - Uses pyttsx3 / Windows SAPI.
    - Keeps TTS synchronous and predictable.
    - Adds detailed diagnostics.
    - Avoids unnecessary voice enumeration during every call.
    - Safely stops the engine.
    - Designed to avoid microphone/TTS resource conflicts.

IMPORTANT:
    This module does not execute commands.
    It only speaks the final response.
"""

from typing import Optional
import os
import re
import shutil
import subprocess


class TextToSpeech:

    # =========================================================
    # INITIALIZATION
    # =========================================================

    def __init__(
        self,
        rate: int = 165,
        volume: float = 1.0,
        debug: bool = True
    ):

        self.engine = None

        self.available = False

        self.error_message = ""

        self.rate = int(rate)

        self.volume = float(volume)

        self.debug = bool(debug)

        self._voices_loaded = False

        self._hindi_voice = None

        self._english_voice = None

        self._current_voice = None
        self._pyttsx3 = None

        # Prefer native Hindi speech when available without making it a startup requirement.
        # If no Hindi voice/eSpeak is installed, retain the Windows SAPI fallback.
        self.tts_mode = os.environ.get("VYOM_TTS_MODE", "auto").strip().lower()

        self._initialize()

    # =========================================================
    # DEBUG
    # =========================================================

    def _log(self, message):

        if not self.debug:
            return

        try:
            print("[TTS] " + str(message), flush=True)
        except Exception:
            pass

    # =========================================================
    # INITIALIZE
    # =========================================================

    def _initialize(self):

        self._log("Initializing Text-To-Speech...")

        try:

            import pyttsx3

            self._log("Importing pyttsx3: OK")

            self.engine = pyttsx3.init()

            if self.engine is None:
                raise RuntimeError(
                    "pyttsx3 returned no engine."
                )

            self._log("SAPI engine initialized.")

            try:
                self.engine.setProperty(
                    "rate",
                    self.rate
                )
            except Exception:
                pass

            try:
                self.engine.setProperty(
                    "volume",
                    self.volume
                )
            except Exception:
                pass

            self.available = True

            self.error_message = ""

            self._load_voices()

            self._log("TTS READY.")

        except Exception as error:

            self.engine = None

            self.available = False

            self.error_message = str(error)

            self._log(
                "TTS initialization failed: "
                + self.error_message
            )

    # =========================================================
    # LOAD VOICES
    # =========================================================

    def _load_voices(self):

        if self.engine is None:
            return

        if self._voices_loaded:
            return

        self._log("Loading available SAPI voices...")

        try:

            voices = self.engine.getProperty(
                "voices"
            ) or []

        except Exception as error:

            self._log(
                "Voice enumeration failed: "
                + str(error)
            )

            self._voices_loaded = True

            return

        for voice in voices:

            try:

                identity = " ".join(
                    str(
                        getattr(
                            voice,
                            attr,
                            ""
                        )
                    )
                    for attr in (
                        "id",
                        "name",
                        "languages"
                    )
                ).lower()

                # -----------------------------------------
                # Hindi voice
                # -----------------------------------------

                hindi_keywords = (
                    "hindi",
                    "hi-in",
                    "hi_in",
                    "hindi india",
                    "kalpana",
                    "heera",
                    "hemant"
                )

                if (
                    self._hindi_voice is None
                    and any(
                        keyword in identity
                        for keyword in hindi_keywords
                    )
                ):

                    self._hindi_voice = voice

                # -----------------------------------------
                # English voice
                # -----------------------------------------

                english_keywords = (
                    "english",
                    "en-in",
                    "en_in",
                    "en-us",
                    "en_gb",
                    "en-gb"
                )

                if (
                    self._english_voice is None
                    and any(
                        keyword in identity
                        for keyword in english_keywords
                    )
                ):

                    self._english_voice = voice

            except Exception:

                continue

        self._voices_loaded = True

        self._log(
            "Voice scan completed. "
            "Hindi="
            + str(self._hindi_voice is not None)
            + ", English="
            + str(self._english_voice is not None)
        )

    # =========================================================
    # STATUS
    # =========================================================

    def is_available(self):

        return self.available

    # =========================================================
    # VOICE SELECTION
    # =========================================================

    def _select_voice_for_text(self, text):

        if self.engine is None:
            return

        self._load_voices()

        value = str(
            text or ""
        )

        is_hindi = bool(
            re.search(
                r"[\u0900-\u097F]",
                value
            )
        )

        voice = (
            self._hindi_voice
            if is_hindi
            else self._english_voice
        )

        if voice is None:
            return

        if voice is self._current_voice:
            return

        try:

            self.engine.setProperty(
                "voice",
                voice.id
            )

            self._current_voice = voice

            self._log(
                "Voice selected: "
                + str(
                    getattr(
                        voice,
                        "name",
                        voice.id
                    )
                )
            )

        except Exception as error:

            self._log(
                "Voice selection failed: "
                + str(error)
            )

    def _create_fresh_engine(self):

        # pyttsx3.init() caches engines by driver. Remove the old cache entry
        # after stopping the previous engine so each speech turn receives a
        # genuinely new SAPI engine rather than a reused object.
        if self._pyttsx3 is None:
            import pyttsx3
            self._pyttsx3 = pyttsx3

        active_engines = getattr(self._pyttsx3, "_activeEngines", None)
        if active_engines is not None:
            for key in (None, "sapi5"):
                try:
                    active_engines.pop(key, None)
                except Exception:
                    pass

        engine = self._pyttsx3.init("sapi5")
        if engine is None:
            raise RuntimeError("pyttsx3 returned no engine.")

        try:
            engine.setProperty("rate", self.rate)
        except Exception:
            pass
        try:
            engine.setProperty("volume", self.volume)
        except Exception:
            pass

        self._log("Fresh SAPI engine created for speech turn.")
        return engine

    @staticmethod
    def _voice_identity(voice):
        return " ".join(
            str(getattr(voice, attr, ""))
            for attr in ("id", "name", "languages")
        ).lower()

    def _has_hindi_sapi_voice(self, engine=None):
        engine = engine or self.engine
        if engine is None:
            return False
        try:
            voices = engine.getProperty("voices") or []
        except Exception:
            return False
        markers = ("hindi", "hi-in", "hi_in", "kalpana", "hemant")
        return any(
            any(marker in self._voice_identity(voice) for marker in markers)
            for voice in voices
        )

    def _find_espeak_ng(self):
        candidates = [shutil.which("espeak-ng"), shutil.which("espeak-ng.exe")]
        roots = [
            os.environ.get("ProgramFiles", r"C:\Program Files"),
            os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)"),
            os.environ.get("LOCALAPPDATA", ""),
        ]
        for root in roots:
            if root:
                candidates.extend((
                    os.path.join(root, "eSpeak NG", "espeak-ng.exe"),
                    os.path.join(root, "eSpeak NG", "espeak-ng"),
                ))
        return next((path for path in candidates if path and os.path.isfile(path)), None)

    def _speak_with_espeak_wav(self, executable, text):
        """Render Hindi speech to WAV, then play it through Windows audio."""
        temporary_path = None
        try:
            import tempfile
            import winsound

            timeout = max(15, min(45, int(len(str(text)) / 8) + 15))
            kwargs = {"check": True, "capture_output": True, "timeout": timeout}
            if os.name == "nt":
                kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
            rendered = subprocess.run(
                [executable, "-v", "hi", "--stdout", str(text)], **kwargs
            )
            audio = getattr(rendered, "stdout", None)
            if not isinstance(audio, (bytes, bytearray)):
                raise RuntimeError("eSpeak NG returned no WAV bytes")
            audio = bytes(audio)
            if not audio.startswith(b"RIFF") or b"WAVE" not in audio[:16]:
                raise RuntimeError("eSpeak NG did not return a valid WAV stream")

            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as stream:
                temporary_path = stream.name
                stream.write(audio)
                stream.flush()

            # Validate PCM before playback. A successful PlaySound return does
            # not prove that the selected physical speaker was audible.
            import wave
            with wave.open(temporary_path, "rb") as wav_file:
                channels = wav_file.getnchannels()
                sample_width = wav_file.getsampwidth()
                sample_rate = wav_file.getframerate()
                frame_count = wav_file.getnframes()
                compression = wav_file.getcomptype()
                if (
                    channels not in (1, 2)
                    or sample_width not in (1, 2, 3, 4)
                    or sample_rate < 8000
                    or frame_count <= 0
                    or compression != "NONE"
                ):
                    raise RuntimeError("eSpeak NG returned unsupported/empty PCM audio")
                duration = frame_count / float(sample_rate)
                if duration < 0.10 or duration > 180:
                    raise RuntimeError("eSpeak NG WAV duration is outside safe limits")
                sample_data = wav_file.readframes(min(frame_count, sample_rate))
                if sample_width == 1:
                    has_signal = any(sample != 128 for sample in sample_data)
                else:
                    has_signal = any(sample_data)
                if not has_signal:
                    raise RuntimeError("eSpeak NG WAV contains digital silence")

            flags = getattr(winsound, "SND_FILENAME", 0) | getattr(winsound, "SND_SYNC", 0)
            winsound.PlaySound(temporary_path, flags)
            self._log(
                "Hindi WAV playback API returned. Physical speaker audibility "
                "still requires user confirmation."
            )
            return {
                "success": True,
                "stage": "playback_api_completed",
                "audio_output_status": "audibility_unverified",
                "audible_output_verified": False,
                "text": str(text),
                "message": (
                    "Hindi WAV was validated and the Windows playback API returned; "
                    "physical speaker audibility is not independently verified."
                ),
                "audio": {
                    "channels": channels,
                    "sample_width_bytes": sample_width,
                    "sample_rate_hz": sample_rate,
                    "duration_seconds": round(duration, 3),
                    "non_silent": True,
                },
            }
        except Exception as error:
            self._log("Hindi WAV playback path failed: " + type(error).__name__)
            return {
                "success": False, "text": str(text or ""),
                "message": "Hindi WAV playback failed: " + type(error).__name__,
            }
        finally:
            if temporary_path:
                try:
                    os.unlink(temporary_path)
                except OSError:
                    pass

    def _speak_with_espeak(self, text):
        executable = self._find_espeak_ng()
        if not executable:
            self._log(
                "Hindi SAPI voice is not installed and eSpeak NG was not found. "
                "Install eSpeak NG (Windows x64) or add a genuine Hindi SAPI voice."
            )
            return {
                "success": False, "text": str(text or ""),
                "message": "Hindi TTS voice is not installed. Install eSpeak NG or a compatible Hindi SAPI voice.",
            }
        try:
            if os.name == "nt":
                self._log("Rendering Hindi speech to WAV for Windows audio playback.")
                wav_result = self._speak_with_espeak_wav(executable, text)
                if wav_result.get("success"):
                    return wav_result
                self._log("WAV playback failed; falling back to direct eSpeak playback.")

            self._log("Using local eSpeak NG Hindi voice (hi); no cloud TTS is used.")
            kwargs = {
                "check": True, "capture_output": True, "text": True,
                "timeout": max(15, min(45, int(len(str(text)) / 8) + 15)),
            }
            if os.name == "nt":
                kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
            subprocess.run([executable, "-v", "hi", str(text)], **kwargs)
            return {"success": True, "text": str(text), "message": "Speech completed with local eSpeak NG Hindi voice."}
        except Exception as error:
            self._log("eSpeak NG Hindi speech failed: " + type(error).__name__)
            return {"success": False, "text": str(text or ""), "message": "Local Hindi TTS failed: " + type(error).__name__}

    def _select_voice_on_engine(self, engine, text):
        try:
            voices = engine.getProperty("voices") or []
        except Exception as error:
            self._log("Voice enumeration failed for speech turn: " + str(error))
            voices = []

        value = str(text or "")
        is_hindi = bool(re.search(r"[\u0900-\u097F]", value))
        hindi_keywords = ("hindi", "hi-in", "hi_in", "hi-in", "hindi india", "kalpana", "heera", "hemant")
        indian_english_keywords = ("en-in", "en_in", "indian english", "english india", "english (india)")
        english_keywords = ("english", "en-us", "en_gb", "en-gb", "en-us")

        def first_matching(markers):
            for candidate in voices:
                identity = self._voice_identity(candidate)
                if any(marker in identity for marker in markers):
                    return candidate
            return None

        selected = first_matching(hindi_keywords) if is_hindi else None
        if selected is None and is_hindi:
            # Do not silently choose the first installed voice (often US
            # Microsoft David) when an Indian English SAPI voice is present.
            selected = first_matching(indian_english_keywords)
            if selected is not None:
                self._log(
                    "Hindi SAPI voice unavailable; using Indian English fallback: "
                    + str(getattr(selected, "name", selected.id))
                )
            elif voices:
                selected = voices[0]
                self._log(
                    "Hindi SAPI voice is not installed; using available fallback: "
                    + str(getattr(selected, "name", selected.id))
                    + ". Install a Hindi SAPI voice for native Hindi pronunciation."
                )
        elif selected is None:
            # Prefer an Indian English voice for mixed Hindi-English command
            # names; only then fall back to another installed English voice.
            selected = first_matching(indian_english_keywords) or first_matching(english_keywords)
            if selected is None and voices:
                selected = voices[0]

        if selected is not None:
            try:
                engine.setProperty("voice", selected.id)
                self._log("Speech voice selected: " + str(getattr(selected, "name", selected.id)))
            except Exception as error:
                self._log("Speech voice selection failed: " + str(error))

    def _play_audio_test_tone(self):
        """Play a short local PCM tone through the Windows default audio route."""
        if os.name != "nt":
            return {
                "success": False,
                "stage": "unsupported_platform",
                "message": "The Windows speaker test is available only on Windows.",
                "audible_output_verified": False,
            }

        temporary_path = None
        try:
            import math
            import struct
            import tempfile
            import wave
            import winsound

            sample_rate = 22050
            duration = 0.55
            frequency = 880.0
            frame_count = int(sample_rate * duration)
            frames = bytearray()
            for index in range(frame_count):
                envelope = min(1.0, index / 350.0, (frame_count - index) / 350.0)
                sample = int(10000 * envelope * math.sin(
                    2.0 * math.pi * frequency * index / sample_rate
                ))
                frames.extend(struct.pack("<h", sample))

            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as stream:
                temporary_path = stream.name

            with wave.open(temporary_path, "wb") as wav_file:
                wav_file.setnchannels(1)
                wav_file.setsampwidth(2)
                wav_file.setframerate(sample_rate)
                wav_file.writeframes(bytes(frames))

            flags = (
                getattr(winsound, "SND_FILENAME", 0)
                | getattr(winsound, "SND_SYNC", 0)
            )
            winsound.PlaySound(temporary_path, flags)
            self._log(
                "Speaker test tone playback API returned; physical audibility "
                "must be confirmed by the user."
            )
            return {
                "success": True,
                "stage": "playback_api_completed",
                "message": "Windows tone playback API returned.",
                "audible_output_verified": False,
            }
        except Exception as error:
            self._log("Speaker test tone failed: " + type(error).__name__)
            return {
                "success": False,
                "stage": "playback_failed",
                "message": "Windows tone playback failed: " + type(error).__name__,
                "audible_output_verified": False,
            }
        finally:
            if temporary_path:
                try:
                    os.unlink(temporary_path)
                except OSError:
                    pass

    def run_audio_diagnostic(self):
        """Exercise tone, English SAPI and the normal Hindi TTS route separately."""
        tone = self._play_audio_test_tone()
        english = self.speak("Vyom audio test. Can you hear this voice?")
        hindi = self.speak("नमस्ते। यह व्योम की हिंदी आवाज़ जाँच है।")

        return {
            "tone": tone,
            "english_sapi": {
                "success": bool(english.get("success")) if isinstance(english, dict) else bool(english),
                "stage": str(english.get("stage") or "sapi_call_completed") if isinstance(english, dict) else "sapi_call_completed",
                "message": str(english.get("message") or "") if isinstance(english, dict) else "",
                "audible_output_verified": False,
            },
            "hindi_tts": {
                "success": bool(hindi.get("success")) if isinstance(hindi, dict) else bool(hindi),
                "stage": str(hindi.get("stage") or "tts_call_completed") if isinstance(hindi, dict) else "tts_call_completed",
                "message": str(hindi.get("message") or "") if isinstance(hindi, dict) else "",
                "audible_output_verified": False,
            },
            "audibility_verified": False,
            "next_step": (
                "The user must report whether the tone, English voice, and Hindi voice "
                "were actually audible."
            ),
        }

    # =========================================================
    # SPEAK
    # =========================================================

    def speak(
        self,
        text
    ):

        self._log("speak() called.")

        if not self.available:
            return {
                "success": False,
                "text": str(text or ""),
                "message": "Text-to-Speech is not available: " + self.error_message
            }

        if text is None:
            return {"success": False, "text": "", "message": "Nothing to speak."}

        text = str(text).strip()
        if not text:
            return {"success": False, "text": "", "message": "Nothing to speak."}

        engine = None
        previous = self.engine
        try:
            is_hindi_text = bool(re.search(r"[\u0900-\u097F]", text))
            if previous is not None:
                try:
                    previous.stop()
                except Exception:
                    pass
            # Normal mode respects the Windows default/selected SAPI voice exactly as
            # before. Hindi pronunciation support is optional and must never stop
            # Vyom from responding when a Hindi voice or eSpeak NG is unavailable.
            optional_hindi_modes = {"auto", "hindi", "espeak", "espeak-ng"}
            use_optional_hindi = self.tts_mode in optional_hindi_modes

            if is_hindi_text and use_optional_hindi:
                if self._has_hindi_sapi_voice(previous):
                    engine = self._create_fresh_engine()
                    self.engine = engine
                    self._select_voice_on_engine(engine, text)
                else:
                    local_result = self._speak_with_espeak(text)
                    if local_result.get("success"):
                        return local_result
                    self._log(
                        "Optional Hindi TTS is unavailable; falling back to the "
                        "Windows-selected SAPI voice. Vyom will continue normally."
                    )

            if engine is None:
                engine = self._create_fresh_engine()
                self.engine = engine
                # Do not set a voice in the default mode. SAPI will use the
                # system/user-selected voice; voice choice is never a startup dependency.

            self._log("engine.say() START")
            engine.say(text)
            self._log("engine.say() COMPLETE")

            self._log("engine.runAndWait() START")
            engine.runAndWait()
            self._log("engine.runAndWait() COMPLETE")

            self._log(
                "SAPI synthesis/playback call completed; physical speaker audibility "
                "still requires user confirmation."
            )
            return {
                "success": True,
                "stage": "sapi_call_completed",
                "audio_output_status": "audibility_unverified",
                "audible_output_verified": False,
                "text": text,
                "message": "SAPI speech call completed; audible output is not independently verified.",
            }

        except Exception as error:
            self._log("Speech failed: " + str(error))
            return {
                "success": False,
                "text": text,
                "message": "Text-to-Speech failed: " + str(error)
            }

        finally:
            if engine is not None:
                try:
                    engine.stop()
                except Exception:
                    pass
            self.engine = None
            self._current_voice = None
            self.available = True
            self._log("Speech turn engine released.")

    # =========================================================
    # STOP
    # =========================================================

    def stop(self):

        self._log("Stopping TTS...")

        if self.engine is None:
            return

        try:

            self.engine.stop()

        except Exception:
            pass

        self._log("TTS stopped.")

    # =========================================================
    # SET RATE
    # =========================================================

    def set_rate(
        self,
        rate
    ):

        try:

            self.rate = int(
                rate
            )

        except (
            ValueError,
            TypeError
        ):

            return False

        if self.engine is not None:

            try:

                self.engine.setProperty(
                    "rate",
                    self.rate
                )

            except Exception:
                pass

        return True

    # =========================================================
    # SET VOLUME
    # =========================================================

    def set_volume(
        self,
        volume
    ):

        try:

            self.volume = float(
                volume
            )

        except (
            ValueError,
            TypeError
        ):

            return False

        if self.volume < 0:
            self.volume = 0.0

        if self.volume > 1:
            self.volume = 1.0

        if self.engine is not None:

            try:

                self.engine.setProperty(
                    "volume",
                    self.volume
                )

            except Exception:
                pass

        return True


# =============================================================
# STANDALONE TEST
# =============================================================

def main():

    print("=" * 60)

    print(
        "Vyom AI - Text To Speech Test v0.2"
    )

    print("=" * 60)

    print("")

    tts = TextToSpeech(
        debug=True
    )

    if not tts.is_available():

        print(
            "TTS Status : NOT AVAILABLE"
        )

        print(
            "Reason : "
            + tts.error_message
        )

        return

    print(
        "TTS Status : READY"
    )

    print("")

    result = tts.speak(
        "Hello. Vyom text to speech is working."
    )

    print(
        "Vyom : "
        + result.get(
            "message",
            ""
        )
    )

    tts.stop()


if __name__ == "__main__":

    main()
