# ============================================================
# Project : Vyom AI
# Module  : speech_to_text.py
# Version : 0.4
#
# Purpose:
#     Stable Speech-To-Text foundation for Vyom AI.
#
# Improvements:
#     - Persistent microphone session during Voice Mode.
#     - Controlled Windows audio-device recovery.
#     - WinError 31 never escapes the STT layer.
#     - Silence and unrecognized speech are normal states.
#     - Safe console output.
#     - Hindi + English recognition support.
#     - Wake-mode dual-language recognition.
#     - Prevents Hindi STT from permanently swallowing
#       English wake words such as "Vyom".
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

        # ----------------------------------------------------
        # Persistent voice-session source.
        # ----------------------------------------------------

        self._session_active = False
        self._session_source = None

        # ----------------------------------------------------
        # Recognition configuration.
        # ----------------------------------------------------

        self.preferred_language = "hi-IN"
        self.fallback_language = "en-IN"

        self.recognition_timeout = 4.0

        # ----------------------------------------------------
        # Last recognized text.
        # Useful for diagnostics.
        # ----------------------------------------------------

        self.last_text = ""
        self.last_language = ""

        self._initialize()

    # ========================================================
    # SAFE CONSOLE
    # ========================================================

    @staticmethod
    def _safe_print(*args, **kwargs):

        try:

            print(
                *args,
                **kwargs
            )

        except (
            PermissionError,
            OSError
        ):

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

            # ------------------------------------------------
            # Speech timing.
            # ------------------------------------------------

            self.recognizer.pause_threshold = 0.65

            self.recognizer.non_speaking_duration = 0.35

            self.recognizer.dynamic_energy_threshold = True

            # ------------------------------------------------
            # Network timeout.
            # ------------------------------------------------

            try:

                self.recognizer.operation_timeout = (
                    self.recognition_timeout
                )

            except Exception:

                pass

            # ------------------------------------------------
            # Microphone.
            # ------------------------------------------------

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

            self.error_message = str(
                error
            )

    # ========================================================
    # STATUS
    # ========================================================

    def is_available(self):

        return self.available

    # ========================================================
    # SESSION START
    # ========================================================

    def start_session(self):
        """
        Open one persistent microphone session for complete
        Voice Mode.
        """

        if not self.available:

            return False

        if (
            self._session_active
            and
            self._session_source is not None
        ):

            return True

        for attempt in range(2):

            try:

                if self.microphone is None:

                    import speech_recognition as sr

                    self.microphone = sr.Microphone()

                self._session_source = (
                    self.microphone.__enter__()
                )

                self._session_active = True

                self._calibrated = False

                self.error_message = ""

                self._device_error_count = 0

                return True

            except Exception as error:

                self._session_active = False

                self._session_source = None

                self._last_device_error = str(
                    error
                )

                self.error_message = str(
                    error
                )

                if (
                    attempt == 0
                    and
                    self._is_device_error(error)
                ):

                    self._safe_print(
                        "Vyom : Microphone device is being reconnected...",
                        flush=True
                    )

                    self._close_microphone()

                    time.sleep(
                        0.25
                    )

                    continue

                break

        return False

    # ========================================================
    # SESSION STOP
    # ========================================================

    def stop_session(self):
        """
        Release persistent microphone safely.
        """

        self._close_microphone()

        self._session_active = False

        self._session_source = None

        self._calibrated = False

    # ========================================================
    # CLOSE MICROPHONE
    # ========================================================

    def _close_microphone(self):

        try:

            if (
                self._session_active
                and
                self.microphone is not None
            ):

                try:

                    self.microphone.__exit__(
                        None,
                        None,
                        None
                    )

                except Exception:

                    pass

        finally:

            self._session_active = False

            self._session_source = None

    # ========================================================
    # DEVICE ERROR DETECTION
    # ========================================================

    @staticmethod
    def _is_device_error(
        error
    ):

        error_name = type(
            error
        ).__name__

        error_text = str(
            error
        )

        combined = (
            error_name
            + " "
            + error_text
        ).lower()

        return (
            "winerror 31" in combined
            or
            "device attached to the system is not functioning"
            in combined
            or
            "invalid device" in combined
            or
            error_name in (
                "PermissionError",
                "OSError",
                "IOError"
            )
        )

    # ========================================================
    # AUDIO DEVICE RECOVERY
    # ========================================================

    def _reset_audio_device(self):
        """
        Completely recreate microphone and PyAudio stream.
        """

        self._close_microphone()

        try:

            import speech_recognition as sr

            self.microphone = None

            self.microphone = (
                sr.Microphone()
            )

            self._calibrated = False

            self.error_message = ""

            return True

        except Exception as error:

            self.microphone = None

            self._last_device_error = str(
                error
            )

            self.error_message = str(
                error
            )

            return False

    # ========================================================
    # GOOGLE RECOGNITION
    # ========================================================

    def _recognize_google(
        self,
        audio,
        language
    ):

        return self.recognizer.recognize_google(
            audio,
            language=language
        )

    # ========================================================
    # UPDATE LANGUAGE PREFERENCE
    # ========================================================

    def _update_language_preference(
        self,
        text
    ):

        value = str(
            text or ""
        ).strip()

        if not value:

            return

        has_devanagari = any(
            "\u0900" <= ch <= "\u097F"
            for ch in value
        )

        has_latin = bool(
            re.search(
                r"[A-Za-z]",
                value
            )
        )

        if (
            has_devanagari
            and
            not has_latin
        ):

            self.preferred_language = (
                "hi-IN"
            )

        elif (
            has_latin
            and
            not has_devanagari
        ):

            self.preferred_language = (
                "en-IN"
            )

    # ========================================================
    # RECOGNIZE WITH FALLBACK
    # ========================================================

    def _recognize_with_fallback(
        self,
        audio,
        wake_mode=False
    ):
        """
        Recognize speech using the preferred language.

        Normal command:
            One recognition request first.

        Wake mode:
            If the preferred language does not produce a
            useful result, also try the fallback language.

        This is important because "Vyom" is an English
        wake word while the user's normal conversation may
        be Hindi.
        """

        languages = [
            self.preferred_language
        ]

        # ----------------------------------------------------
        # Wake mode gets an additional language attempt.
        # ----------------------------------------------------

        if wake_mode:

            if (
                self.fallback_language
                not in languages
            ):

                languages.append(
                    self.fallback_language
                )

        last_error = None

        for language in languages:

            try:

                text = self._recognize_google(
                    audio,
                    language
                )

                text = str(
                    text or ""
                ).strip()

                if text:

                    return {
                        "success": True,
                        "text": text,
                        "language": language
                    }

            except Exception as error:

                last_error = error

                error_name = type(
                    error
                ).__name__

                # ------------------------------------------------
                # Unknown speech:
                # Try next language if available.
                # ------------------------------------------------

                if error_name == "UnknownValueError":

                    continue

                # ------------------------------------------------
                # Google/network failure.
                # No point trying another language because the
                # service itself may be unavailable.
                # ------------------------------------------------

                if error_name == "RequestError":

                    return {
                        "success": False,
                        "status": "service_error",
                        "text": "",
                        "language": language,
                        "message": (
                            "Speech recognition service "
                            "is unavailable or timed out."
                        )
                    }

                if (
                    "timeout"
                    in str(
                        error
                    ).lower()
                ):

                    return {
                        "success": False,
                        "status": "service_timeout",
                        "text": "",
                        "language": language,
                        "message": (
                            "Speech recognition took "
                            "too long to respond."
                        )
                    }

                # ------------------------------------------------
                # Other recognition error.
                # Continue to fallback in wake mode.
                # ------------------------------------------------

                if wake_mode:

                    continue

                break

        # ----------------------------------------------------
        # No usable recognition.
        # ----------------------------------------------------

        if last_error is not None:

            error_name = type(
                last_error
            ).__name__

            if error_name == "UnknownValueError":

                return {
                    "success": False,
                    "status": "unrecognized",
                    "text": "",
                    "language": "",
                    "message": ""
                }

        return {
            "success": False,
            "status": "unrecognized",
            "text": "",
            "language": "",
            "message": ""
        }

    # ========================================================
    # LISTEN
    # ========================================================

    def listen(
        self,
        timeout=4,
        phrase_time_limit=7,
        announce=True,
        wake_mode=False
    ):

        if not self.available:

            return {
                "success": False,
                "status": "unavailable",
                "text": "",
                "message": self.error_message
            }

        persistent = (
            self._session_active
        )

        # ----------------------------------------------------
        # Safe timeout values.
        # ----------------------------------------------------

        try:

            timeout = max(
                1.5,
                min(
                    float(timeout),
                    8.0
                )
            )

        except (
            TypeError,
            ValueError
        ):

            timeout = 4.0

        try:

            phrase_time_limit = max(
                2.0,
                min(
                    float(phrase_time_limit),
                    10.0
                )
            )

        except (
            TypeError,
            ValueError
        ):

            phrase_time_limit = 7.0

        # ----------------------------------------------------
        # Two attempts maximum for microphone/device recovery.
        # ----------------------------------------------------

        for attempt in range(2):

            temporary_source = None

            try:

                # =================================================
                # MICROPHONE SOURCE
                # =================================================

                if persistent:

                    if (
                        self._session_source
                        is None
                    ):

                        if not self.start_session():

                            return {
                                "success": False,
                                "status": "device_error",
                                "text": "",
                                "message": (
                                    "The microphone device "
                                    "is not responding."
                                )
                            }

                    source = (
                        self._session_source
                    )

                else:

                    if self.microphone is None:

                        import speech_recognition as sr

                        self.microphone = (
                            sr.Microphone()
                        )

                    temporary_source = (
                        self.microphone.__enter__()
                    )

                    source = (
                        temporary_source
                    )

                # =================================================
                # LISTENING
                # =================================================

                if announce:

                    self._safe_print(
                        "",
                        flush=True
                    )

                    self._safe_print(
                        "Vyom : Listening...",
                        flush=True
                    )

                # ------------------------------------------------
                # Ambient calibration.
                #
                # Only once per complete voice session.
                # ------------------------------------------------

                if not self._calibrated:

                    self._safe_print(
                        "Vyom : Calibrating microphone...",
                        flush=True
                    )

                    self.recognizer.adjust_for_ambient_noise(
                        source,
                        duration=0.25
                    )

                    self._calibrated = True

                    if announce:

                        self._safe_print(
                            "Vyom : Microphone ready.",
                            flush=True
                        )

                # =================================================
                # CAPTURE AUDIO
                # =================================================

                audio = self.recognizer.listen(
                    source,
                    timeout=timeout,
                    phrase_time_limit=phrase_time_limit
                )

                # ------------------------------------------------
                # Release one-shot microphone before recognition.
                # Persistent session stays open.
                # ------------------------------------------------

                if temporary_source is not None:

                    try:

                        self.microphone.__exit__(
                            None,
                            None,
                            None
                        )

                    except Exception:

                        pass

                    temporary_source = None

                self._device_error_count = 0

                if announce:

                    self._safe_print(
                        "Vyom : Processing speech...",
                        flush=True
                    )

                # =================================================
                # RECOGNITION
                # =================================================

                recognition = (
                    self._recognize_with_fallback(
                        audio,
                        wake_mode=wake_mode
                    )
                )

                if not recognition.get(
                    "success",
                    False
                ):

                    return {
                        "success": False,
                        "status": recognition.get(
                            "status",
                            "unrecognized"
                        ),
                        "text": "",
                        "language": "",
                        "message": recognition.get(
                            "message",
                            ""
                        )
                    }

                text = str(
                    recognition.get(
                        "text",
                        ""
                    )
                ).strip()

                language = (
                    recognition.get(
                        "language",
                        ""
                    )
                )

                if not text:

                    return {
                        "success": False,
                        "status": "unrecognized",
                        "text": "",
                        "language": "",
                        "message": ""
                    }

                # ------------------------------------------------
                # Save diagnostics.
                # ------------------------------------------------

                self.last_text = text

                self.last_language = language

                self._update_language_preference(
                    text
                )

                return {
                    "success": True,
                    "status": "recognized",
                    "text": text,
                    "language": (
                        "hindi"
                        if any(
                            "\u0900" <= ch <= "\u097F"
                            for ch in text
                        )
                        else "english"
                    ),
                    "recognition_language": language,
                    "message": text
                }

            except Exception as error:

                # ------------------------------------------------
                # Release temporary microphone.
                # ------------------------------------------------

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

                error_name = type(
                    error
                ).__name__

                error_text = str(
                    error
                )

                # =================================================
                # SILENCE
                # =================================================

                if error_name == "WaitTimeoutError":

                    return {
                        "success": False,
                        "status": "silence",
                        "text": "",
                        "message": ""
                    }

                # =================================================
                # UNRECOGNIZED SPEECH
                # =================================================

                if error_name == "UnknownValueError":

                    return {
                        "success": False,
                        "status": "unrecognized",
                        "text": "",
                        "message": ""
                    }

                # =================================================
                # GOOGLE SERVICE ERROR
                # =================================================

                if error_name == "RequestError":

                    return {
                        "success": False,
                        "status": "service_error",
                        "text": "",
                        "message": (
                            "Speech recognition service "
                            "is unavailable or timed out."
                        )
                    }

                # =================================================
                # DEVICE ERROR
                # =================================================

                is_device_error = (
                    self._is_device_error(
                        error
                    )
                )

                if (
                    is_device_error
                    and
                    attempt == 0
                ):

                    self._device_error_count += 1

                    self._last_device_error = (
                        error_text
                    )

                    self._safe_print(
                        "Vyom : Microphone connection was interrupted. Recovering...",
                        flush=True
                    )

                    self._close_microphone()

                    if self._reset_audio_device():

                        time.sleep(
                            0.25
                        )

                        if persistent:

                            if self.start_session():

                                continue

                        else:

                            continue

                # =================================================
                # OTHER ERROR
                # =================================================

                return {
                    "success": False,
                    "status": (
                        "device_error"
                        if is_device_error
                        else "error"
                    ),
                    "text": "",
                    "message": (
                        "The microphone device is not responding."
                        if is_device_error
                        else (
                            "Speech recognition failed: "
                            + error_text
                        )
                    )
                }

        # ========================================================
        # FINAL FAILURE
        # ========================================================

        return {
            "success": False,
            "status": "device_error",
            "text": "",
            "message": (
                "The microphone device is not responding."
            )
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
            phrase_time_limit=phrase_time_limit,
            announce=True,
            wake_mode=False
        )

        if result.get(
            "success",
            False
        ):

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

            self._safe_print(
                "Vyom : Speech recognition is not available."
            )

            self._safe_print(
                "Reason : "
                + self.error_message
            )

            return False

        self._safe_print(
            "Vyom : Microphone is ready."
        )

        result = self.listen(
            timeout=5,
            phrase_time_limit=8,
            announce=True,
            wake_mode=False
        )

        if result.get(
            "success",
            False
        ):

            self._safe_print(
                "You : "
                + result.get(
                    "text",
                    ""
                )
            )

            return True

        self._safe_print(
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

    print(
        "=" * 60
    )

    print(
        "Vyom AI - Speech To Text Test"
    )

    print(
        "=" * 60
    )

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

        return

    print(
        "STT Status : READY"
    )

    try:

        stt.test()

    finally:

        stt.stop_session()


if __name__ == "__main__":

    main()
