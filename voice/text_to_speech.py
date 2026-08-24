"""
Project : Vyom AI
Version : 0.1
Module  : Text To Speech

Purpose:
    Convert Vyom response text into spoken audio.

Flow:

    Vyom Result
         ↓
    TextToSpeech
         ↓
    Windows SAPI / pyttsx3
         ↓
    Speaker

IMPORTANT:

    This module does not execute commands.
    It only speaks the final response.

    Existing SpeechToText behaviour remains unchanged.
"""

from typing import Optional


class TextToSpeech:

    # =========================================================
    # INITIALIZATION
    # =========================================================

    def __init__(
        self,
        rate: int = 165,
        volume: float = 1.0
    ):

        self.engine = None

        self.available = False

        self.error_message = ""

        self.rate = int(rate)

        self.volume = float(volume)

        self._initialize()

    # =========================================================
    # INITIALIZE
    # =========================================================

    def _initialize(self):

        try:

            import pyttsx3

            self.engine = pyttsx3.init()

            self.engine.setProperty(
                "rate",
                self.rate
            )

            self.engine.setProperty(
                "volume",
                self.volume
            )

            self.available = True

            self.error_message = ""

        except Exception as error:

            self.engine = None

            self.available = False

            self.error_message = str(
                error
            )

    # =========================================================
    # STATUS
    # =========================================================

    def is_available(self):

        return self.available

    # =========================================================
    # SPEAK
    # =========================================================

    def speak(
        self,
        text
    ):

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
                "message": (
                    "Nothing to speak."
                )
            }

        text = str(
            text
        ).strip()

        if not text:

            return {
                "success": False,
                "text": "",
                "message": (
                    "Nothing to speak."
                )
            }

        try:

            self.engine.say(
                text
            )

            self.engine.runAndWait()

            return {
                "success": True,
                "text": text,
                "message": (
                    "Speech completed."
                )
            }

        except Exception as error:

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

        if self.engine is None:

            return

        try:

            self.engine.stop()

        except Exception:

            pass

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
        "Vyom AI - Text To Speech Test"
    )

    print("=" * 60)

    print("")

    tts = TextToSpeech()

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


if __name__ == "__main__":

    main()
