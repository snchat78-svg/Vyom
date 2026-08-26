# ============================================================
# Project : Vyom AI
# Module  : speech_to_text.py
# Version : 0.1
#
# Purpose:
#     Basic Speech-to-Text foundation for Vyom AI
#
# Designed for:
#     Windows 8.1 / Windows 10 / Windows 11
#
# Current Stage:
#     Microphone -> Speech -> Text
#
# IMPORTANT:
#     This module does NOT connect to ToolManager yet.
#     Existing Vyom functionality remains untouched.
# ============================================================

import sys


class SpeechToText:

    # ========================================================
    # INITIALIZATION
    # ========================================================

    def __init__(self):

        self.recognizer = None
        self.microphone = None

        self.available = False
        self.error_message = ""

        self._initialize()

    # ========================================================
    # INITIALIZE SPEECH RECOGNITION
    # ========================================================

    def _initialize(self):

        try:

            import speech_recognition as sr

            self.recognizer = sr.Recognizer()
            self.microphone = sr.Microphone()

            self.available = True
            self.error_message = ""

        except ImportError:

            self.available = False

            self.error_message = (
                "SpeechRecognition package is not installed."
            )

        except Exception as error:

            self.available = False

            self.error_message = str(error)

    # ========================================================
    # STATUS
    # ========================================================

    def is_available(self):

        return self.available

    # ========================================================
    # LISTEN
    # ========================================================

    def listen(
        self,
        timeout=5,
        phrase_time_limit=8,
        announce=True
    ):

        if not self.available:

            return {
                "success": False,
                "status": "unavailable",
                "text": "",
                "message": self.error_message
            }

        try:

            with self.microphone as source:

                if announce:
                    print("")
                    print("Vyom : Listening...")

                # Adjust microphone for surrounding noise.
                self.recognizer.adjust_for_ambient_noise(
                    source,
                    duration=0.5
                )

                audio = self.recognizer.listen(
                    source,
                    timeout=timeout,
                    phrase_time_limit=phrase_time_limit
                )

            if announce:
                print("Vyom : Processing speech...")

            # ------------------------------------------------
            # First STT backend
            #
            # Google Web Speech recognition is used only for
            # this initial testing stage.
            #
            # Later we can add offline STT without changing
            # the public listen() interface.
            # ------------------------------------------------

            # Try Hindi first, then Indian English.  The same audio can be
            # decoded by both language models; when the Hindi result contains
            # Devanagari we prefer it, otherwise the English result is used.
            candidates = []

            for language in ("hi-IN", "en-IN", "en-US"):
                try:
                    candidate = self.recognizer.recognize_google(
                        audio,
                        language=language
                    )
                    candidate = str(candidate or "").strip()
                    if candidate:
                        candidates.append((language, candidate))
                except Exception:
                    continue

            if not candidates:
                return {
                    "success": False,
                    "status": "unrecognized",
                    "text": "",
                    "message": "I could not understand the speech."
                }

            hindi_candidates = [
                text for language, text in candidates
                if language == "hi-IN" and any("\u0900" <= ch <= "\u097F" for ch in text)
            ]

            if hindi_candidates:
                text = hindi_candidates[0]
                detected_language = "hindi"
            else:
                text = next(
                    (text for language, text in candidates if language == "en-IN"),
                    candidates[-1][1]
                )
                detected_language = "english"

            return {
                "success": True,
                "status": "recognized",
                "text": text,
                "language": detected_language,
                "message": text
            }

        except Exception as error:

            error_name = type(
                error
            ).__name__

            if error_name == "WaitTimeoutError":

                # Silence is a normal conversational state.
                # It is NOT a command failure.
                return {
                    "success": False,
                    "status": "silence",
                    "text": "",
                    "message": ""
                }

            elif error_name == "UnknownValueError":

                return {
                    "success": False,
                    "status": "unrecognized",
                    "text": "",
                    "message": (
                        "I could not understand what you said."
                    )
                }

            elif error_name == "RequestError":

                message = (
                    "Speech recognition service "
                    "is unavailable."
                )

                status = "service_error"

            else:

                message = (
                    "Speech recognition failed: "
                    + str(error)
                )

                status = "error"

            return {
                "success": False,
                "status": status,
                "text": "",
                "message": message
            }

    # ========================================================
    # SIMPLE TEXT RESULT
    # ========================================================

    def recognize(
        self,
        timeout=5,
        phrase_time_limit=8
    ):

        result = self.listen(
            timeout=timeout,
            phrase_time_limit=phrase_time_limit
        )

        if result.get("success"):

            return result.get(
                "text",
                ""
            )

        return ""

    # ========================================================
    # TEST MICROPHONE
    # ========================================================

    def test(self):

        if not self.available:

            print(
                "Vyom : Speech recognition is not available."
            )

            print(
                "Reason : "
                + self.error_message
            )

            return False

        print(
            "Vyom : Microphone is ready."
        )

        result = self.listen()

        if result.get("success"):

            print(
                "You : "
                + result.get(
                    "text",
                    ""
                )
            )

            return True

        print(
            "Vyom : "
            + result.get(
                "message",
                "Speech recognition failed."
            )
        )

        return False


# ============================================================
# STANDALONE TEST
# ============================================================

def main():

    print("=" * 60)
    print("Vyom AI - Speech To Text Test")
    print("=" * 60)
    print("")

    stt = SpeechToText()

    if not stt.is_available():

        print(
            "STT Status : NOT AVAILABLE"
        )

        print(
            "Reason : "
            + stt.error_message
        )

        print("")
        print(
            "No existing Vyom module was changed."
        )

        return

    print(
        "STT Status : READY"
    )

    print("")
    print(
        "Speak a short sentence after"
        " 'Listening...' appears."
    )

    print(
        "Press Ctrl+C to stop."
    )

    print("")

    try:

        while True:

            result = stt.listen()

            if result.get("success"):

                print(
                    "You : "
                    + result.get(
                        "text",
                        ""
                    )
                )

            else:

                print(
                    "Vyom : "
                    + result.get(
                        "message",
                        "Speech recognition failed."
                    )
                )

            print("")

    except KeyboardInterrupt:

        print("")
        print(
            "Vyom : Voice test stopped."
        )


if __name__ == "__main__":

    main()

