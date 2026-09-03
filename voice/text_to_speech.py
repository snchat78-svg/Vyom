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
import re


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
                "message": (
                    "Text-to-Speech is not available: "
                    + self.error_message
                )
            }

        if text is None:

            return {
                "success": False,
                "text": "",
                "message": "Nothing to speak."
            }

        text = str(
            text
        ).strip()

        if not text:

            return {
                "success": False,
                "text": "",
                "message": "Nothing to speak."
            }

        try:

            self._select_voice_for_text(
                text
            )

            self._log(
                "engine.say() START"
            )

            self.engine.say(
                text
            )

            self._log(
                "engine.say() COMPLETE"
            )

            self._log(
                "engine.runAndWait() START"
            )

            self.engine.runAndWait()

            self._log(
                "engine.runAndWait() COMPLETE"
            )

            return {
                "success": True,
                "text": text,
                "message": "Speech completed."
            }

        except Exception as error:

            self._log(
                "Speech failed: "
                + str(error)
            )

            return {
                "success": False,
                "text": text,
                "message": (
                    "Text-to-Speech failed: "
                    + str(error)
                )
            }

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
