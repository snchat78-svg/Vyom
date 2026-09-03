# ============================================================
# Project : Vyom AI
# Module  : speech_to_text.py
# Version : 0.6
#
# Purpose:
#     Stable Speech-To-Text foundation for Vyom AI Voice Mode.
#
# Version 0.6 goals:
#     - Persistent microphone session during Voice Mode.
#     - No blocking ambient-noise calibration at startup.
#     - Adaptive energy threshold for speech detection.
#     - Visible wake-word listening diagnostics.
#     - Hindi + English recognition support.
#     - Wake-mode dual-language recognition.
#     - Keeps English wake words such as "Vyom" from being
#       permanently swallowed by Hindi recognition.
#     - Controlled Windows audio-device recovery.
#     - WinError 31 stays inside the STT layer.
#     - Silence and unrecognized speech are normal states.
#     - Stable result dictionary compatible with VoiceController.
#     - Existing recognize() and test() interfaces preserved.
# ============================================================

import re
import time


class SpeechToText:
    """Speech recognition service used by Vyom voice mode."""

    # ========================================================
    # INITIALIZATION
    # ========================================================
    def __init__(self):
        self.recognizer = None
        self.microphone = None

        self.available = False
        self.error_message = ""

        # Persistent microphone-session state.
        self._session_active = False
        self._session_source = None

        # Calibration is intentionally NOT required in v0.6.
        # This avoids startup hangs on older Windows/PyAudio setups.
        self._calibrated = False

        # Device recovery diagnostics.
        self._device_error_count = 0
        self._last_device_error = ""

        # Recognition configuration.
        self.preferred_language = "hi-IN"
        self.fallback_language = "en-IN"
        self.recognition_timeout = 4.0

        # Audio configuration.
        self.enable_ambient_calibration = False
        self.initial_energy_threshold = 250
        self.dynamic_energy_adjustment_damping = 0.15
        self.dynamic_energy_ratio = 1.5

        # Diagnostics.
        self.debug_wake = True
        self.last_text = ""
        self.last_language = ""
        self.last_status = ""

        self._initialize()

    # ========================================================
    # SAFE CONSOLE
    # ========================================================
    @staticmethod
    def _safe_print(*args, **kwargs):
        try:
            print(*args, **kwargs)
        except (PermissionError, OSError):
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
            self.recognizer.phrase_threshold = 0.20

            # ------------------------------------------------
            # Adaptive energy detection.
            #
            # IMPORTANT:
            # No mandatory adjust_for_ambient_noise() call.
            # This prevents startup blocking on older systems.
            # ------------------------------------------------
            self.recognizer.dynamic_energy_threshold = True

            self.recognizer.energy_threshold = (
                self.initial_energy_threshold
            )

            self.recognizer.dynamic_energy_adjustment_damping = (
                self.dynamic_energy_adjustment_damping
            )

            self.recognizer.dynamic_energy_ratio = (
                self.dynamic_energy_ratio
            )

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
            # Microphone object.
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
    # SESSION START
    # ========================================================
    def start_session(self):
        """
        Open one persistent microphone session for Voice Mode.
        """

        if not self.available:
            return False

        if (
            self._session_active
            and self._session_source is not None
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

                self._safe_print(
                    "Vyom : Microphone ready (adaptive mode)",
                    flush=True
                )

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
                    and self._is_device_error(error)
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
        Release the persistent microphone safely.
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
                and self.microphone is not None
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
            "no default input device" in combined
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
    # AUDIO DEVICE RESET
    # ========================================================
    def _reset_audio_device(self):
        """
        Recreate the microphone object after a device failure.
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
    # LANGUAGE PREFERENCE
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
    # WAKE WORD NORMALIZATION
    # ========================================================
    @staticmethod
    def _normalize_wake_text(
        text
    ):

        value = str(
            text or ""
        ).lower().strip()

        value = value.replace(
            "।",
            " "
        )

        value = value.replace(
            ".",
            " "
        )

        value = value.replace(
            ",",
            " "
        )

        value = value.replace(
            "!",
            " "
        )

        value = value.replace(
            "?",
            " "
        )

        value = value.replace(
            "'",
            ""
        )

        value = value.replace(
            '"',
            ""
        )

        return " ".join(
            value.split()
        )

    # ========================================================
    # WAKE WORD CHECK
    # ========================================================
    @classmethod
    def _looks_like_vyom(
        cls,
        text
    ):

        normalized = (
            cls._normalize_wake_text(
                text
            )
        )

        if not normalized:
            return False

        aliases = (
            "vyom",
            "viyom",
            "veyom",
            "veyam",
            "vyam",
            "viom",
            "vyom ji",
            "hey vyom",
            "hey viyom",
            "hey veyom",
            "हे व्योम",
            "व्योम",
            "व्योम जी",
            "हे व्योम",
        )

        # Exact aliases.
        if normalized in aliases:
            return True

        # Individual-word matching.
        words = normalized.split()

        for word in words:

            if word in (
                "vyom",
                "viyom",
                "veyom",
                "veyam",
                "vyam",
                "viom",
                "व्योम",
            ):

                return True

        # Small spelling-error tolerance.
        try:

            import difflib

            for word in words:

                ratio = (
                    difflib.SequenceMatcher(
                        None,
                        word,
                        "vyom"
                    ).ratio()
                )

                if ratio >= 0.78:
                    return True

        except Exception:
            pass

        return False

    # ========================================================
    # RECOGNIZE WITH FALLBACK
    # ========================================================
    def _recognize_with_fallback(
        self,
        audio,
        wake_mode=False
    ):
        """
        Normal mode:

            Preferred language first.

        Wake mode:

            Hindi and English are both tried.

            The result is accepted as a wake result only when
            it actually looks like "Vyom".

        This prevents a valid Hindi transcript from swallowing
        an English wake word.
        """

        preferred = (
            self.preferred_language
            or
            "hi-IN"
        )

        fallback = (
            self.fallback_language
            or
            "en-IN"
        )

        languages = [
            preferred
        ]

        if fallback not in languages:

            languages.append(
                fallback
            )

        results = []

        last_error = None

        for language in languages:

            try:

                if (
                    wake_mode
                    and
                    self.debug_wake
                ):

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

                    results.append(
                        {
                            "text": text,
                            "language": language
                        }
                    )

                    # --------------------------------------------
                    # Normal command mode.
                    # --------------------------------------------
                    if not wake_mode:

                        return {
                            "success": True,
                            "status": "recognized",
                            "text": text,
                            "language": language
                        }

                    # --------------------------------------------
                    # Wake mode.
                    #
                    # Accept immediately when this language
                    # actually recognized the wake word.
                    # --------------------------------------------
                    if self._looks_like_vyom(
                        text
                    ):

                        return {
                            "success": True,
                            "status": "recognized",
                            "text": text,
                            "language": language
                        }

            except Exception as error:

                last_error = error

                error_name = type(
                    error
                ).__name__

                # --------------------------------------------
                # Speech not understood.
                # Try the other language.
                # --------------------------------------------
                if (
                    error_name
                    ==
                    "UnknownValueError"
                ):

                    continue

                # --------------------------------------------
                # Google/network service error.
                # --------------------------------------------
                if (
                    error_name
                    ==
                    "RequestError"
                ):

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

                # --------------------------------------------
                # Timeout.
                # --------------------------------------------
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

                # --------------------------------------------
                # Wake mode:
                # Try fallback language.
                # --------------------------------------------
                if wake_mode:
                    continue

                break

        # ====================================================
        # WAKE MODE DIAGNOSTIC RESULT
        # ====================================================
        if (
            wake_mode
            and
            results
        ):

            for item in results:

                self._safe_print(
                    "Vyom : Wake speech -> "
                    + item["text"],
                    flush=True
                )

            return {
                "success": False,
                "status": "unrecognized",
                "text": "",
                "language": "",
                "message": ""
            }

        # ====================================================
        # NO USABLE RECOGNITION
        # ====================================================
        if last_error is not None:

            if (
                type(
                    last_error
                ).__name__
                ==
                "UnknownValueError"
            ):

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
    # SAFE TIMEOUT
    # ========================================================
    @staticmethod
    def _safe_timeout(
        value,
        default=4.0,
        minimum=1.5,
        maximum=8.0
    ):

        try:

            return max(
                minimum,
                min(
                    float(value),
                    maximum
                )
            )

        except (
            TypeError,
            ValueError
        ):

            return default

    # ========================================================
    # SAFE PHRASE TIME LIMIT
    # ========================================================
    @staticmethod
    def _safe_phrase_limit(
        value,
        default=7.0,
        minimum=2.0,
        maximum=10.0
    ):

        try:

            return max(
                minimum,
                min(
                    float(value),
                    maximum
                )
            )

        except (
            TypeError,
            ValueError
        ):

            return default

    # ========================================================
    # LISTEN
    # ========================================================
    def listen(
        self,
        timeout=4,
        phrase_time_limit=7,
        announce=True,
        wake_mode=None
    ):
        """
        Capture one utterance.

        Compatibility behavior:

            announce=False is treated as wake-listening mode
            when wake_mode is not explicitly supplied.

        This is important because the existing VoiceController
        calls listen_once() with announce=False while waiting
        for "Vyom".
        """

        if not self.available:

            self.last_status = (
                "unavailable"
            )

            return {
                "success": False,
                "status": "unavailable",
                "text": "",
                "language": "",
                "message": self.error_message
            }

        # ----------------------------------------------------
        # Existing VoiceController does not explicitly pass
        # wake_mode. It uses announce=False for wake listening.
        # ----------------------------------------------------
        if wake_mode is None:

            wake_mode = not announce

        timeout = self._safe_timeout(
            timeout
        )

        phrase_time_limit = (
            self._safe_phrase_limit(
                phrase_time_limit
            )
        )

        persistent = (
            self._session_active
        )

        # ====================================================
        # MICROPHONE ATTEMPTS
        # ====================================================
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

                            self.last_status = (
                                "device_error"
                            )

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
                # VISIBLE LISTENING DIAGNOSTICS
                # =================================================
                if wake_mode:

                    if self.debug_wake:

                        self._safe_print(
                            "Vyom : Listening for wake word...",
                            flush=True
                        )

                        self._safe_print(
                            "Vyom : Wake threshold = "
                            + str(
                                getattr(
                                    self.recognizer,
                                    "energy_threshold",
                                    "unknown"
                                )
                            ),
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
                # OPTIONAL CALIBRATION
                # =================================================
                #
                # Disabled by default.
                #
                # If explicitly enabled, it runs once per
                # persistent microphone session.
                #
                # =================================================
                if (
                    self.enable_ambient_calibration
                    and
                    not self._calibrated
                ):

                    if (
                        announce
                        or
                        wake_mode
                    ):

                        self._safe_print(
                            "Vyom : Calibrating microphone...",
                            flush=True
                        )

                    self.recognizer.adjust_for_ambient_noise(
                        source,
                        duration=0.25
                    )

                    self._calibrated = True

                    if (
                        announce
                        or
                        wake_mode
                    ):

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

                # -------------------------------------------------
                # Close temporary microphone only.
                # Persistent microphone remains open.
                # -------------------------------------------------
                if (
                    temporary_source
                    is not None
                ):

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
                if (
                    wake_mode
                    and
                    self.debug_wake
                ):

                    self._safe_print(
                        "Vyom : Audio captured. "
                        "Processing wake word...",
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

                    self.last_status = (
                        recognition.get(
                            "status",
                            "unrecognized"
                        )
                    )

                    return {
                        "success": False,
                        "status": self.last_status,
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
                    or ""
                ).strip()

                recognition_language = (
                    recognition.get(
                        "language",
                        ""
                    )
                )

                if not text:

                    self.last_status = (
                        "unrecognized"
                    )

                    return {
                        "success": False,
                        "status": "unrecognized",
                        "text": "",
                        "language": "",
                        "message": ""
                    }

                # =================================================
                # SAVE DIAGNOSTICS
                # =================================================
                self.last_text = text

                self.last_language = (
                    recognition_language
                )

                self.last_status = (
                    "recognized"
                )

                self._update_language_preference(
                    text
                )

                # =================================================
                # WAKE RESULT
                # =================================================
                if (
                    wake_mode
                    and
                    self.debug_wake
                ):

                    self._safe_print(
                        "Vyom : Wake speech -> "
                        + text,
                        flush=True
                    )

                # =================================================
                # FINAL RESULT
                # =================================================
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
                    "recognition_language": (
                        recognition_language
                    ),
                    "message": text
                }

            except Exception as error:

                # =================================================
                # RELEASE TEMPORARY MICROPHONE
                # =================================================
                if (
                    temporary_source
                    is not None
                ):

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
                if (
                    error_name
                    ==
                    "WaitTimeoutError"
                ):

                    self.last_status = (
                        "silence"
                    )

                    if (
                        wake_mode
                        and
                        self.debug_wake
                    ):

                        self._safe_print(
                            "Vyom : No speech detected. Waiting...",
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
                # UNRECOGNIZED SPEECH
                # =================================================
                if (
                    error_name
                    ==
                    "UnknownValueError"
                ):

                    self.last_status = (
                        "unrecognized"
                    )

                    if (
                        wake_mode
                        and
                        self.debug_wake
                    ):

                        self._safe_print(
                            "Vyom : Speech was not understood. Waiting...",
                            flush=True
                        )

                    return {
                        "success": False,
                        "status": "unrecognized",
                        "text": "",
                        "language": "",
                        "message": ""
                    }

                # =================================================
                # GOOGLE SERVICE ERROR
                # =================================================
                if (
                    error_name
                    ==
                    "RequestError"
                ):

                    self.last_status = (
                        "service_error"
                    )

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
                # DEVICE ERROR / WINERROR 31 RECOVERY
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
                        "Vyom : Microphone connection "
                        "was interrupted. Recovering...",
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
                self.last_status = (
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
                    )
                }

        # ========================================================
        # FINAL DEVICE FAILURE
        # ========================================================
        self.last_status = (
            "device_error"
        )

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
    # LISTEN ONCE
    #
    # Direct STT compatibility helper.
    # ========================================================
    def listen_once(
        self,
        announce=False,
        timeout=4,
        phrase_time_limit=7
    ):

        return self.listen(
            timeout=timeout,
            phrase_time_limit=phrase_time_limit,
            announce=announce,
            wake_mode=(
                not announce
            )
        )

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
                "Vyom : Speech was not recognized."
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

    print("")

    try:

        stt.test()

    finally:

        stt.stop_session()


if __name__ == "__main__":
    main()
