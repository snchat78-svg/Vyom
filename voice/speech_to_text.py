# ============================================================
# Project : Vyom AI
# Module  : speech_to_text.py
# Version : 0.3
#
# Purpose:
#     Stable Speech-To-Text foundation for Vyom AI.
#
# Improvements:
#     - Persistent microphone session during Voice Mode.
#     - Controlled Windows audio-device recovery.
#     - WinError 31 never escapes the STT layer.
#     - Silence and unrecognized speech are normal states.
#     - Safe console output so a console/device error cannot crash Vyom.
# ============================================================

import sys
import re
import time


class SpeechToText:

    # ========================================================
    # INITIALIZATION
    # ========================================================

    def __init__(self):

        self.recognizer = None
        self.microphone = None

        self.available = False
        self.error_message = ""

        self._calibrated = False
        self._device_error_count = 0
        self._last_device_error = ""

        # Persistent voice-session source.
        # Keeping one PyAudio stream alive avoids repeatedly opening and
        # closing the microphone on older Windows/PyAudio combinations.
        self._session_active = False
        self._session_source = None

        self._initialize()

    # ========================================================
    # SAFE CONSOLE
    # ========================================================

    @staticmethod
    def _safe_print(*args, **kwargs):

        try:
            print(*args, **kwargs)
        except (PermissionError, OSError):
            # A broken Windows console must never terminate the voice agent.
            pass
        except Exception:
            pass

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
            self._calibrated = False
            self._device_error_count = 0
            self._last_device_error = ""

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
    # SESSION START
    # ========================================================

    def start_session(self):
        """Open one microphone session for the complete Voice Mode."""

        if not self.available:
            return False

        if self._session_active and self._session_source is not None:
            return True

        for attempt in range(2):

            try:

                if self.microphone is None:
                    import speech_recognition as sr
                    self.microphone = sr.Microphone()

                self._session_source = self.microphone.__enter__()
                self._session_active = True
                self._calibrated = False
                self.error_message = ""
                self._device_error_count = 0
                return True

            except Exception as error:

                self._session_active = False
                self._session_source = None
                self._last_device_error = str(error)
                self.error_message = str(error)

                if attempt == 0 and self._is_device_error(error):
                    self._safe_print(
                        "Vyom : Microphone device is being reconnected...",
                        flush=True
                    )
                    self._close_microphone()
                    time.sleep(0.25)
                    continue

                break

        return False

    # ========================================================
    # SESSION STOP
    # ========================================================

    def stop_session(self):
        """Release the persistent microphone session safely."""

        self._close_microphone()
        self._session_active = False
        self._session_source = None
        self._calibrated = False

    # ========================================================
    # CLOSE MICROPHONE
    # ========================================================

    def _close_microphone(self):

        try:
            if self._session_active and self.microphone is not None:
                try:
                    self.microphone.__exit__(None, None, None)
                except Exception:
                    pass
        finally:
            self._session_active = False
            self._session_source = None

    # ========================================================
    # DEVICE ERROR DETECTION
    # ========================================================

    @staticmethod
    def _is_device_error(error):

        error_name = type(error).__name__
        error_text = str(error)
        combined = (error_name + " " + error_text).lower()

        return (
            "winerror 31" in combined
            or "device attached to the system is not functioning" in combined
            or "invalid device" in combined
            or error_name in ("PermissionError", "OSError", "IOError")
        )

    # ========================================================
    # AUDIO DEVICE RECOVERY
    # ========================================================

    def _reset_audio_device(self):
        """Completely recreate the microphone and its PyAudio stream."""

        self._close_microphone()

        try:
            import speech_recognition as sr

            self.microphone = None
            self.microphone = sr.Microphone()
            self._calibrated = False
            self.error_message = ""
            return True

        except Exception as error:
            self.microphone = None
            self._last_device_error = str(error)
            self.error_message = str(error)
            return False

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

        # Voice Mode uses a persistent source. Standalone calls still work
        # with the old one-shot microphone behavior.
        persistent = self._session_active

        for attempt in range(2):

            temporary_source = None

            try:

                if persistent:

                    if self._session_source is None:
                        if not self.start_session():
                            return {
                                "success": False,
                                "status": "device_error",
                                "text": "",
                                "message": "The microphone device is not responding."
                            }

                    source = self._session_source

                else:

                    if self.microphone is None:
                        import speech_recognition as sr
                        self.microphone = sr.Microphone()

                    temporary_source = self.microphone.__enter__()
                    source = temporary_source

                if announce:
                    self._safe_print("", flush=True)
                    self._safe_print(
                        "Vyom : Listening...",
                        flush=True
                    )

                if not self._calibrated:
                    self.recognizer.adjust_for_ambient_noise(
                        source,
                        duration=0.35
                    )
                    self._calibrated = True

                audio = self.recognizer.listen(
                    source,
                    timeout=timeout,
                    phrase_time_limit=phrase_time_limit
                )

                # For one-shot calls release the stream before the network
                # recognition request. Voice Mode keeps its stream alive.
                if temporary_source is not None:
                    try:
                        self.microphone.__exit__(None, None, None)
                    except Exception:
                        pass
                    temporary_source = None

                self._device_error_count = 0

                if announce:
                    self._safe_print(
                        "Vyom : Processing speech...",
                        flush=True
                    )

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
                        "message": ""
                    }

                hindi_candidates = [
                    text for language, text in candidates
                    if language == "hi-IN"
                    and any("\u0900" <= ch <= "\u097F" for ch in text)
                ]

                if hindi_candidates:
                    text = hindi_candidates[0]
                    detected_language = "hindi"
                else:
                    text = next(
                        (
                            text for language, text in candidates
                            if language == "en-IN"
                        ),
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

                # Always close a temporary one-shot microphone after an
                # exception. Never leave a half-open PyAudio stream behind.
                if temporary_source is not None:
                    try:
                        self.microphone.__exit__(
                            type(error),
                            error,
                            error.__traceback__
                        )
                    except Exception:
                        pass
                    temporary_source = None

                error_name = type(error).__name__
                error_text = str(error)
                combined = (error_name + " " + error_text).lower()

                if error_name == "WaitTimeoutError":
                    return {
                        "success": False,
                        "status": "silence",
                        "text": "",
                        "message": ""
                    }

                if error_name == "UnknownValueError":
                    return {
                        "success": False,
                        "status": "unrecognized",
                        "text": "",
                        "message": ""
                    }

                if error_name == "RequestError":
                    return {
                        "success": False,
                        "status": "service_error",
                        "text": "",
                        "message": "Speech recognition service is unavailable."
                    }

                is_device_error = self._is_device_error(error)

                if is_device_error and attempt == 0:

                    self._device_error_count += 1
                    self._last_device_error = error_text

                    self._safe_print(
                        "Vyom : Microphone device temporarily stopped responding. Recovering...",
                        flush=True
                    )

                    self._close_microphone()

                    if self._reset_audio_device():
                        time.sleep(0.35)

                        # Recreate the persistent source immediately if Voice
                        # Mode is active, otherwise the next listen will do it.
                        if persistent:
                            if self.start_session():
                                continue
                        else:
                            continue

                return {
                    "success": False,
                    "status": "device_error" if is_device_error else "error",
                    "text": "",
                    "message": (
                        "The microphone device is not responding."
                        if is_device_error
                        else "Speech recognition failed: " + error_text
                    )
                }

        return {
            "success": False,
            "status": "device_error",
            "text": "",
            "message": "The microphone device is not responding."
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
            return result.get("text", "")

        return ""

    # ========================================================
    # TEST MICROPHONE
    # ========================================================

    def test(self):

        if not self.available:

            self._safe_print(
                "Vyom : Speech recognition is not available."
            )

            self._safe_print(
                "Reason : " + self.error_message
            )

            return False

        self._safe_print(
            "Vyom : Microphone is ready."
        )

        result = self.listen()

        if result.get("success"):

            self._safe_print(
                "You : " + result.get("text", "")
            )

            return True

        self._safe_print(
            "Vyom : " + result.get(
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

        print("STT Status : NOT AVAILABLE")
        print("Reason : " + stt.error_message)
        return

    print("STT Status : READY")

    try:
        stt.test()
    finally:
        stt.stop_session()


if __name__ == "__main__":
    main()
