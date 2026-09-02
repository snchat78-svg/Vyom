# ============================================================
# Project : Vyom AI
# Module  : speech_to_text.py
# Version : 0.5
#
# Purpose:
#     Stable Speech-To-Text foundation for Vyom AI.
#
# Design Goals:
#     - Persistent microphone session during Voice Mode.
#     - Windows 8 / 8.1 friendly audio handling.
#     - WinError 31 must never escape STT layer.
#     - Microphone calibration must never block Voice Mode.
#     - Adaptive microphone energy handling.
#     - Hindi + English recognition.
#     - Wake-mode dual-language recognition.
#     - Silence is a normal state.
#     - Unrecognized speech is a normal state.
#     - Safe microphone recovery.
#     - Safe console output.
#     - Compatible result structure for VoiceController.
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

        # ----------------------------------------------------
        # Calibration state.
        #
        # IMPORTANT:
        # Ambient calibration is NOT allowed to block the
        # complete Voice Mode.
        # ----------------------------------------------------

        self._calibrated = False

        # Calibration is deliberately disabled by default.
        #
        # Why?
        #
        # On some Windows 8 / 8.1 audio drivers,
        # adjust_for_ambient_noise() can block while waiting
        # for a valid audio stream.
        #
        # Dynamic energy threshold is already enabled.
        #

        self.enable_ambient_calibration = False

        self.calibration_duration = 0.20

        # ----------------------------------------------------
        # Device diagnostics.
        # ----------------------------------------------------

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
        # ----------------------------------------------------

        self.last_text = ""
        self.last_language = ""

        # ----------------------------------------------------
        # Internal state.
        # ----------------------------------------------------

        self._last_status = ""
        self._last_message = ""

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

            # ------------------------------------------------
            # Dynamic threshold.
            #
            # This allows SpeechRecognition to adapt to the
            # microphone environment without requiring the
            # blocking ambient calibration step.
            # ------------------------------------------------

            self.recognizer.dynamic_energy_threshold = True

            try:

                self.recognizer.dynamic_energy_adjustment_damping = (
                    0.15
                )

            except Exception:

                pass

            try:

                self.recognizer.dynamic_energy_ratio = (
                    1.5
                )

            except Exception:

                pass

            # ------------------------------------------------
            # Initial energy value.
            #
            # Keep it moderate so that normal microphones can
            # detect speech without mandatory calibration.
            # Dynamic threshold can adjust from here.
            # ------------------------------------------------

            try:

                self.recognizer.energy_threshold = 300

            except Exception:

                pass

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

        This method never allows a microphone initialization
        exception to escape the STT layer.
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

                # ------------------------------------------------
                # Open microphone.
                # ------------------------------------------------

                self._session_source = (
                    self.microphone.__enter__()
                )

                self._session_active = True

                # ------------------------------------------------
                # Calibration state is reset for the new
                # physical microphone stream.
                # ------------------------------------------------

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

                    self._reset_audio_device()

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
    # AUDIO DEVICE RECOVERY
    # ========================================================

    def _reset_audio_device(self):
        """
        Completely recreate microphone object.

        Important:
        This does NOT allow an audio exception to escape.
        """

        self._close_microphone()

        try:

            import speech_recognition as sr

            self.microphone = None

            # ------------------------------------------------
            # Recreate microphone object.
            # ------------------------------------------------

            self.microphone = sr.Microphone()

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
    # SAFE AMBIENT CALIBRATION
    # ========================================================

    def _prepare_microphone(self, source):
        """
        Prepare microphone for speech recognition.

        IMPORTANT:
        Blocking ambient calibration is disabled by default.

        Dynamic energy threshold remains active and handles
        normal background-noise adaptation during listening.

        This function is intentionally isolated so calibration
        can be enabled later without changing listen().
        """

        if self._calibrated:

            return True

        # ----------------------------------------------------
        # Safe default path.
        #
        # Do NOT call adjust_for_ambient_noise() here.
        # It can block on some Windows 8 / 8.1 audio devices.
        # ----------------------------------------------------

        if not self.enable_ambient_calibration:

            self._calibrated = True

            self._safe_print(
                "Vyom : Microphone ready (adaptive mode).",
                flush=True
            )

            return True

        # ----------------------------------------------------
        # Optional calibration path.
        #
        # This is protected by try/except. If calibration
        # fails, Voice Mode continues using adaptive mode.
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

            self._last_device_error = str(
                error
            )

            # ------------------------------------------------
            # Calibration failure must NOT stop Voice Mode.
            # ------------------------------------------------

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
        Recognize speech using preferred language.

        Normal mode:
            Preferred language first.

        Wake mode:
            Preferred language + fallback language.

        This keeps Hindi conversation natural while allowing
        English wake words such as "Vyom".
        """

        languages = []

        # ----------------------------------------------------
        # Preferred language.
        # ----------------------------------------------------

        if self.preferred_language:

            languages.append(
                self.preferred_language
            )

        # ----------------------------------------------------
        # Wake mode gets both languages.
        # ----------------------------------------------------

        if wake_mode:

            if (
                self.fallback_language
                and
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
                # Unknown speech.
                # Try next language.
                # ------------------------------------------------

                if error_name == "UnknownValueError":

                    continue

                # ------------------------------------------------
                # Network/service failure.
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

                # ------------------------------------------------
                # Timeout.
                # ------------------------------------------------

                if (
                    "timeout"
                    in str(
                        error
                    ).lower()
                ):

                    if wake_mode:

                        continue

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
                # Try fallback during wake mode.
                # ------------------------------------------------

                if wake_mode:

                    continue

                break

        # ----------------------------------------------------
        # Final recognition status.
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
                "language": "",
                "message": self.error_message
            }

        persistent = (
            self._session_active
        )

        # ----------------------------------------------------
        # Safe timeout.
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
        # Safe phrase limit.
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

        # ----------------------------------------------------
        # Maximum two attempts.
        #
        # Attempt 1 = normal microphone.
        # Attempt 2 = recreated microphone after device error.
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
                # MICROPHONE PREPARATION
                # =================================================

                # ------------------------------------------------
                # Do not print "Listening..." after every silent
                # wake check unless caller explicitly requests it.
                # ------------------------------------------------

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
                # Safe microphone preparation.
                # This can NEVER intentionally block Voice Mode
                # on ambient calibration.
                # ------------------------------------------------

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
                # CAPTURE AUDIO
                # =================================================

                audio = self.recognizer.listen(
                    source,
                    timeout=timeout,
                    phrase_time_limit=phrase_time_limit
                )

                # ------------------------------------------------
                # Release temporary microphone.
                # Persistent microphone remains open.
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

                # ------------------------------------------------
                # Processing message.
                # ------------------------------------------------

                if announce:

                    self._safe_print(
                        "Vyom : Processing speech...",
                        flush=True
                    )

                # =================================================
                # GOOGLE SPEECH RECOGNITION
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

                    self._last_status = (
                        recognition.get(
                            "status",
                            "unrecognized"
                        )
                    )

                    self._last_message = (
                        recognition.get(
                            "message",
                            ""
                        )
                    )

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

                # ------------------------------------------------
                # Extract recognized text.
                # ------------------------------------------------

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

                self._last_status = "recognized"

                self._last_message = text

                self._update_language_preference(
                    text
                )

                # ------------------------------------------------
                # Determine user-facing language.
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
                # RELEASE TEMPORARY MICROPHONE
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

                error_text = str(
                    error
                )

                # =================================================
                # SILENCE
                # =================================================

                if error_name == "WaitTimeoutError":

                    self._last_status = "silence"

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
                # GOOGLE SERVICE ERROR
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

                                # ------------------------------------------------
                                # Important:
                                # New microphone = new stream.
                                # Preparation will happen again safely.
                                # ------------------------------------------------

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
                    )
                }

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

        # ----------------------------------------------------
        # Open persistent microphone for test.
        # ----------------------------------------------------

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
