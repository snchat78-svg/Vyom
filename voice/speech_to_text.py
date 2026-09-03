# ============================================================
# Project : Vyom AI
# Module  : speech_to_text.py
# Version : 0.6
#
# Purpose:
#     Stable Speech-To-Text foundation for Vyom AI.
#
# Design:
#     - Persistent microphone session.
#     - Windows 8 / 8.1 friendly.
#     - WinError 31 recovery.
#     - No blocking ambient calibration by default.
#     - Adaptive microphone mode.
#     - Hindi + English recognition.
#     - Wake-mode dual-language recognition.
#     - Wake diagnostics.
#     - Silence is a normal state.
#     - Unrecognized speech is a normal state.
#     - Existing VoiceController compatibility preserved.
# ============================================================

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

        # ----------------------------------------------------
        # Calibration
        # ----------------------------------------------------

        self._calibrated = False

        # IMPORTANT:
        # Disabled by default because some Windows 8/8.1
        # audio devices can block inside adjust_for_ambient_noise.
        self.enable_ambient_calibration = False

        self.calibration_duration = 0.20

        # ----------------------------------------------------
        # Device state
        # ----------------------------------------------------

        self._device_error_count = 0
        self._last_device_error = ""

        # ----------------------------------------------------
        # Persistent microphone session
        # ----------------------------------------------------

        self._session_active = False
        self._session_source = None

        # ----------------------------------------------------
        # Language
        # ----------------------------------------------------

        self.preferred_language = "hi-IN"
        self.fallback_language = "en-IN"

        self.recognition_timeout = 4.0

        # ----------------------------------------------------
        # Diagnostics
        # ----------------------------------------------------

        self.last_text = ""
        self.last_language = ""

        self._last_status = ""
        self._last_message = ""

        self._initialize()

    # ========================================================
    # SAFE PRINT
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
    # INITIALIZE
    # ========================================================

    def _initialize(self):

        try:

            import speech_recognition as sr

            self.recognizer = sr.Recognizer()

            # ------------------------------------------------
            # Speech settings
            # ------------------------------------------------

            self.recognizer.pause_threshold = 0.65

            self.recognizer.non_speaking_duration = 0.35

            self.recognizer.dynamic_energy_threshold = True

            try:

                self.recognizer.dynamic_energy_adjustment_damping = 0.15

            except Exception:

                pass

            try:

                self.recognizer.dynamic_energy_ratio = 1.5

            except Exception:

                pass

            # ------------------------------------------------
            # Initial energy threshold.
            #
            # This is deliberately moderate for old laptop
            # microphones.
            # ------------------------------------------------

            try:

                self.recognizer.energy_threshold = 250

            except Exception:

                pass

            # ------------------------------------------------
            # Google/network timeout
            # ------------------------------------------------

            try:

                self.recognizer.operation_timeout = (
                    self.recognition_timeout
                )

            except Exception:

                pass

            # ------------------------------------------------
            # Microphone
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

            self.error_message = str(error)

    # ========================================================
    # STATUS
    # ========================================================

    def is_available(self):

        return self.available

    # ========================================================
    # START SESSION
    # ========================================================

    def start_session(self):

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

                self._last_device_error = str(error)

                self.error_message = str(error)

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

                    time.sleep(0.30)

                    if self._reset_audio_device():

                        continue

                break

        return False

    # ========================================================
    # STOP SESSION
    # ========================================================

    def stop_session(self):

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
    def _is_device_error(error):

        error_name = type(error).__name__

        error_text = str(error)

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
            "input overflowed" in combined
            or
            "input device" in combined
            or
            error_name in (
                "PermissionError",
                "OSError",
                "IOError"
            )
        )

    # ========================================================
    # RESET AUDIO DEVICE
    # ========================================================

    def _reset_audio_device(self):

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
    # MICROPHONE PREPARATION
    # ========================================================

    def _prepare_microphone(self, source):

        if self._calibrated:

            return True

        # ----------------------------------------------------
        # Default adaptive mode.
        # ----------------------------------------------------

        if not self.enable_ambient_calibration:

            self._calibrated = True

            self._safe_print(
                "Vyom : Microphone ready (adaptive mode).",
                flush=True
            )

            return True

        # ----------------------------------------------------
        # Optional calibration.
        # ----------------------------------------------------

        self._safe_print(
            "Vyom : Calibrating microphone...",
            flush=True
        )

        try:

            self.recognizer.adjust_for_ambient_noise(
                source,
                duration=self.calibration_duration
            )

            self._calibrated = True

            self._safe_print(
                "Vyom : Microphone ready.",
                flush=True
            )

            return True

        except Exception as error:

            self._last_device_error = str(error)

            self._calibrated = True

            self._safe_print(
                "Vyom : Calibration skipped. Adaptive microphone mode active.",
                flush=True
            )

            return True

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
    # LANGUAGE PREFERENCE
    # ========================================================

    def _update_language_preference(self, text):

        value = str(text or "").strip()

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

            self.preferred_language = "hi-IN"

        elif (
            has_latin
            and
            not has_devanagari
        ):

            self.preferred_language = "en-IN"

    # ========================================================
    # WAKE WORD CHECK
    # ========================================================

    @staticmethod
    def _looks_like_vyom(text):

        value = str(
            text or ""
        ).lower().strip()

        if not value:

            return False

        # ----------------------------------------------------
        # Remove punctuation.
        # ----------------------------------------------------

        normalized = re.sub(
            r"[^a-zA-Z0-9\u0900-\u097F\s]",
            " ",
            value
        )

        normalized = re.sub(
            r"\s+",
            " ",
            normalized
        ).strip()

        # ----------------------------------------------------
        # Common English STT variations.
        # ----------------------------------------------------

        aliases = (
            "vyom",
            "viyom",
            "veyom",
            "veyam",
            "vyam",
            "viom",
            "vyo",
            "vyom ji",
            "hey vyom",
            "hey viyom",
            "hey veyom",
        )

        for alias in aliases:

            if alias in normalized:

                return True

        # ----------------------------------------------------
        # Hindi Devanagari forms.
        # ----------------------------------------------------

        hindi_aliases = (
            "व्योम",
            "वियॉम",
            "वियम",
            "व्योम जी",
        )

        for alias in hindi_aliases:

            if alias in normalized:

                return True

        return False

    # ========================================================
    # RECOGNIZE WITH FALLBACK
    # ========================================================

    def _recognize_with_fallback(
        self,
        audio,
        wake_mode=False
    ):

        # ----------------------------------------------------
        # Normal command mode.
        # ----------------------------------------------------

        if not wake_mode:

            languages = [
                self.preferred_language
            ]

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

                    if error_name == "UnknownValueError":

                        continue

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
                        in str(error).lower()
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

                    break

            return {
                "success": False,
                "status": "unrecognized",
                "text": "",
                "language": "",
                "message": ""
            }

        # ====================================================
        # WAKE MODE
        #
        # IMPORTANT:
        # Try BOTH languages.
        #
        # We do not stop merely because Hindi recognition
        # returned some unrelated successful text.
        # ====================================================

        languages = []

        if self.preferred_language:

            languages.append(
                self.preferred_language
            )

        if (
            self.fallback_language
            and
            self.fallback_language
            not in languages
        ):

            languages.append(
                self.fallback_language
            )

        successful_results = []

        service_error = None

        for language in languages:

            try:

                self._safe_print(
                    "Vyom : Wake recognition -> "
                    + language,
                    flush=True
                )

                text = self._recognize_google(
                    audio,
                    language
                )

                text = str(
                    text or ""
                ).strip()

                if text:

                    successful_results.append(
                        {
                            "success": True,
                            "text": text,
                            "language": language
                        }
                    )

                    # ------------------------------------------------
                    # If this result clearly contains Vyom,
                    # immediately use it.
                    # ------------------------------------------------

                    if self._looks_like_vyom(
                        text
                    ):

                        self._safe_print(
                            "Vyom : Wake word candidate -> "
                            + text,
                            flush=True
                        )

                        return {
                            "success": True,
                            "text": text,
                            "language": language
                        }

            except Exception as error:

                error_name = type(
                    error
                ).__name__

                if error_name == "UnknownValueError":

                    continue

                if error_name == "RequestError":

                    service_error = error

                    continue

                if (
                    "timeout"
                    in str(error).lower()
                ):

                    continue

                continue

        # ----------------------------------------------------
        # If no wake-specific result was found but one language
        # did understand something, return that result.
        #
        # VoiceController can decide whether it is a wake word.
        # ----------------------------------------------------

        if successful_results:

            return successful_results[0]

        if service_error is not None:

            return {
                "success": False,
                "status": "service_error",
                "text": "",
                "language": "",
                "message": (
                    "Speech recognition service "
                    "is unavailable."
                )
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
                "language": "",
                "message": self.error_message
            }

        persistent = self._session_active

        # ----------------------------------------------------
        # Timeout
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

        # ----------------------------------------------------
        # Phrase limit
        # ----------------------------------------------------

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

        # ====================================================
        # TWO ATTEMPTS MAXIMUM
        # ====================================================

        for attempt in range(2):

            temporary_source = None

            try:

                # =================================================
                # SOURCE
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
                                "language": "",
                                "message": (
                                    "The microphone device "
                                    "is not responding."
                                )
                            }

                    source = self._session_source

                else:

                    if self.microphone is None:

                        import speech_recognition as sr

                        self.microphone = sr.Microphone()

                    temporary_source = (
                        self.microphone.__enter__()
                    )

                    source = temporary_source

                # =================================================
                # LISTEN MESSAGE
                # =================================================

                if wake_mode:

                    self._safe_print(
                        "Vyom : Listening for wake word...",
                        flush=True
                    )

                elif announce:

                    self._safe_print(
                        "",
                        flush=True
                    )

                    self._safe_print(
                        "Vyom : Listening...",
                        flush=True
                    )

                # =================================================
                # MICROPHONE PREPARATION
                # =================================================

                if not self._prepare_microphone(
                    source
                ):

                    return {
                        "success": False,
                        "status": "device_error",
                        "text": "",
                        "language": "",
                        "message": (
                            "The microphone could not "
                            "be prepared."
                        )
                    }

                # =================================================
                # CAPTURE
                # =================================================

                audio = self.recognizer.listen(
                    source,
                    timeout=timeout,
                    phrase_time_limit=phrase_time_limit
                )

                # ------------------------------------------------
                # Temporary microphone release.
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

                # =================================================
                # AUDIO CAPTURED
                # =================================================

                if wake_mode:

                    self._safe_print(
                        "Vyom : Audio captured. Processing wake word...",
                        flush=True
                    )

                elif announce:

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

                    status = recognition.get(
                        "status",
                        "unrecognized"
                    )

                    self._last_status = status

                    self._last_message = (
                        recognition.get(
                            "message",
                            ""
                        )
                    )

                    if wake_mode:

                        if status == "service_error":

                            self._safe_print(
                                "Vyom : Wake recognition service error.",
                                flush=True
                            )

                        elif status == "unrecognized":

                            self._safe_print(
                                "Vyom : Wake speech not recognized.",
                                flush=True
                            )

                    return {
                        "success": False,
                        "status": status,
                        "text": "",
                        "language": "",
                        "message": recognition.get(
                            "message",
                            ""
                        )
                    }

                # =================================================
                # TEXT
                # =================================================

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
                # Diagnostics
                # ------------------------------------------------

                self.last_text = text

                self.last_language = language

                self._last_status = "recognized"

                self._last_message = text

                self._update_language_preference(
                    text
                )

                if wake_mode:

                    self._safe_print(
                        "Vyom : Wake speech -> "
                        + text,
                        flush=True
                    )

                elif announce:

                    self._safe_print(
                        "You : "
                        + text,
                        flush=True
                    )

                # ------------------------------------------------
                # User-facing language
                # ------------------------------------------------

                detected_language = (
                    "hindi"
                    if any(
                        "\u0900" <= ch <= "\u097F"
                        for ch in text
                    )
                    else "english"
                )

                return {
                    "success": True,
                    "status": "recognized",
                    "text": text,
                    "language": detected_language,
                    "recognition_language": language,
                    "message": text
                }

            except Exception as error:

                # =================================================
                # TEMPORARY SOURCE RELEASE
                # =================================================

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

                error_text = str(error)

                # =================================================
                # SILENCE
                # =================================================

                if error_name == "WaitTimeoutError":

                    self._last_status = "silence"

                    if wake_mode:

                        self._safe_print(
                            "Vyom : No wake speech detected.",
                            flush=True
                        )

                    return {
                        "success": False,
                        "status": "silence",
                        "text": "",
                        "language": "",
                        "message": ""
                    }

                # =================================================
                # UNRECOGNIZED
                # =================================================

                if error_name == "UnknownValueError":

                    self._last_status = "unrecognized"

                    return {
                        "success": False,
                        "status": "unrecognized",
                        "text": "",
                        "language": "",
                        "message": ""
                    }

                # =================================================
                # GOOGLE SERVICE
                # =================================================

                if error_name == "RequestError":

                    self._last_status = "service_error"

                    return {
                        "success": False,
                        "status": "service_error",
                        "text": "",
                        "language": "",
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

                    self._last_device_error = error_text

                    self._safe_print(
                        "Vyom : Microphone connection was interrupted. Recovering...",
                        flush=True
                    )

                    self._close_microphone()

                    if self._reset_audio_device():

                        time.sleep(
                            0.30
                        )

                        if persistent:

                            if self.start_session():

                                continue

                        else:

                            continue

                # =================================================
                # OTHER ERROR
                # =================================================

                self._last_status = (
                    "device_error"
                    if is_device_error
                    else "error"
                )

                return {
                    "success": False,
                    "status": (
                        "device_error"
                        if is_device_error
                        else "error"
                    ),
                    "text": "",
                    "language": "",
                    "message": (
                        "The microphone device is not responding."
                        if is_device_error
                        else (
                            "Speech recognition failed: "
                            + error_text
                        )
                    }

                )

        # ========================================================
        # FINAL FAILURE
        # ========================================================

        return {
            "success": False,
            "status": "device_error",
            "text": "",
            "language": "",
            "message": (
                "The microphone device is not responding."
            )
        }

    # ========================================================
    # SIMPLE RECOGNIZE
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
    # MICROPHONE TEST
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

            return True

        message = result.get(
            "message",
            ""
        )

        if message:

            self._safe_print(
                "Vyom : "
                + message
            )

        else:

            self._safe_print(
                "Vyom : No speech recognized."
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

        if stt.start_session():

            stt.test()

        else:

            print(
                "Microphone session could not be started."
            )

    finally:

        stt.stop_session()


if __name__ == "__main__":

    main()
