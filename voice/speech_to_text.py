"""
Project : Vyom AI
Version : 1.1
Module  : Speech To Text

Purpose:
    Convert microphone speech into text for Vyom AI.

Voice Input Reliability v1.1

Flow:

    Microphone
        ↓
    Audio Capture
        ↓
    Speech Recognition
        ↓
    Hindi / English fallback
        ↓
    Structured Result
        ↓
    VoiceController / Executor

Important:
    This module ONLY captures and recognizes speech.
    It does not execute commands.

Design goals:
    - Persistent microphone session
    - Windows-friendly device recovery
    - Hindi -> English recognition fallback
    - Wake-word mode
    - Normal command mode
    - Bounded Google recognition requests
    - No indefinite network blocking
    - Graceful silence handling
    - Graceful microphone recovery
    - Backward-compatible public API
"""

import re
import time


class SpeechToText:

    # ---------------------------------------------------------
    # Configuration
    # ---------------------------------------------------------

    recognition_timeout = 4

    # Maximum time allowed for the Google recognition request.
    # This is intentionally separate from microphone timeout.
    google_request_timeout = 8

    initial_energy_threshold = 250

    dynamic_energy_adjustment_damping = 0.15
    dynamic_energy_ratio = 1.5

    pause_threshold = 0.65
    non_speaking_duration = 0.35
    phrase_threshold = 0.20

    # Small delay used during device recovery.
    recovery_delay = 0.35

    # Maximum consecutive device recovery attempts.
    max_device_recovery_attempts = 3

    # ---------------------------------------------------------
    # Constructor
    # ---------------------------------------------------------

    def __init__(
        self,
        preferred_language="hi-IN",
        fallback_language="en-IN",
        debug=True
    ):
        self.recognizer = None
        self.microphone = None

        self.available = False
        self.error_message = ""

        self.debug = bool(debug)

        self.preferred_language = preferred_language
        self.fallback_language = fallback_language

        self._session_active = False
        self._session_source = None

        self._calibrated = False

        self._last_text = ""
        self._last_language = ""
        self._last_status = ""

        self._device_error_count = 0
        self._recognition_error_count = 0

        self._sr_module = None

        self._initialize()

    # ---------------------------------------------------------
    # Logging
    # ---------------------------------------------------------

    def _log(self, message):
        if not self.debug:
            return

        try:
            print("[STT] " + str(message), flush=True)
        except Exception:
            pass

    # ---------------------------------------------------------
    # Initialization
    # ---------------------------------------------------------

    def _initialize(self):
        """
        Initialize SpeechRecognition and microphone.

        This method does not permanently open the microphone.
        The microphone is opened only when a voice session starts.
        """

        self._log("Initializing Speech-To-Text...")

        try:
            import speech_recognition as sr

            self._sr_module = sr

            self._log("speech_recognition import: OK")

            self.recognizer = sr.Recognizer()

            # ---------------------------------------------
            # Recognition tuning
            # ---------------------------------------------

            try:
                self.recognizer.pause_threshold = self.pause_threshold
            except Exception:
                pass

            try:
                self.recognizer.non_speaking_duration = (
                    self.non_speaking_duration
                )
            except Exception:
                pass

            try:
                self.recognizer.phrase_threshold = self.phrase_threshold
            except Exception:
                pass

            try:
                self.recognizer.dynamic_energy_threshold = True
            except Exception:
                pass

            try:
                self.recognizer.energy_threshold = (
                    self.initial_energy_threshold
                )
            except Exception:
                pass

            # ---------------------------------------------
            # Dynamic energy configuration
            # ---------------------------------------------

            try:
                self.recognizer.dynamic_energy_adjustment_damping = (
                    self.dynamic_energy_adjustment_damping
                )
            except Exception:
                pass

            try:
                self.recognizer.dynamic_energy_ratio = (
                    self.dynamic_energy_ratio
                )
            except Exception:
                pass

            # ---------------------------------------------
            # IMPORTANT:
            # SpeechRecognition uses operation_timeout for
            # internal network/API operations.
            #
            # This prevents Google recognition from waiting
            # forever on supported versions.
            # ---------------------------------------------

            try:
                self.recognizer.operation_timeout = (
                    self.google_request_timeout
                )

                self._log(
                    "Google recognition timeout: "
                    + str(self.google_request_timeout)
                    + " seconds"
                )

            except Exception as error:
                self._log(
                    "Could not configure operation timeout: "
                    + str(error)
                )

            # ---------------------------------------------
            # Microphone object creation
            # ---------------------------------------------

            self._log("Checking microphone...")

            self.microphone = sr.Microphone()

            self.available = True
            self.error_message = ""

            self._log("Speech-To-Text READY.")

        except Exception as error:

            self.available = False
            self.error_message = str(error)

            self._log(
                "STT initialization failed: "
                + self.error_message
            )

    # ---------------------------------------------------------
    # Availability
    # ---------------------------------------------------------

    def is_available(self):
        return bool(self.available)

    # ---------------------------------------------------------
    # Device Error Detection
    # ---------------------------------------------------------

    def _is_device_error(self, error):

        message = str(error or "").lower()

        patterns = (
            "winerror 31",
            "device attached",
            "no default input device",
            "invalid input device",
            "input device",
            "permissionerror",
            "audio device",
            "paerror",
            "portaudio",
            "wasapi",
            "directsound",
            "mmdevice",
            "microphone"
        )

        return any(
            pattern in message
            for pattern in patterns
        )

    # ---------------------------------------------------------
    # Recognition Error Detection
    # ---------------------------------------------------------

    def _is_network_error(self, error):

        message = str(error or "").lower()

        patterns = (
            "requesterror",
            "connection",
            "network",
            "urlopen",
            "timed out",
            "timeout",
            "service unavailable",
            "remote end closed",
            "connection reset",
            "connection aborted",
            "connection refused",
            "name or service not known",
            "temporary failure"
        )

        return any(
            pattern in message
            for pattern in patterns
        )

    # ---------------------------------------------------------
    # Audio Device Reset
    # ---------------------------------------------------------

    def _reset_audio_device(self):

        self._log("Resetting microphone state...")

        self._close_microphone()

        self._session_active = False
        self._session_source = None
        self._calibrated = False

        try:
            time.sleep(self.recovery_delay)
        except Exception:
            pass

    # ---------------------------------------------------------
    # Session Recovery
    # ---------------------------------------------------------

    def recover_session(self):

        self._log("Recovery start.")

        self._reset_audio_device()

        # First try the existing microphone object.
        try:
            if self.start_session():
                self._log(
                    "Microphone session restored."
                )
                return True
        except Exception as error:
            self._log(
                "Existing microphone recovery failed: "
                + str(error)
            )

        # Reinitialize SpeechRecognition completely.
        self._log(
            "Reinitializing Speech-To-Text..."
        )

        self._initialize()

        if not self.available:
            self._log(
                "STT reinitialization failed."
            )
            return False

        try:
            restored = self.start_session()

            if restored:
                self._log(
                    "Microphone session restored "
                    "after reinitialization."
                )

            return restored

        except Exception as error:

            self._log(
                "Microphone recovery failed: "
                + str(error)
            )

            return False

    # ---------------------------------------------------------
    # Close Microphone
    # ---------------------------------------------------------

    def _close_microphone(self):

        if self._session_source is None:
            return

        try:
            self._session_source.__exit__(
                None,
                None,
                None
            )
        except Exception:
            pass

        self._session_source = None

    # ---------------------------------------------------------
    # Start Persistent Session
    # ---------------------------------------------------------

    def start_session(self):

        if not self.available:

            self._log(
                "Cannot start session: "
                "STT unavailable."
            )

            return False

        if self._session_active:

            self._log(
                "Session already active."
            )

            return True

        self._log(
            "Opening microphone session..."
        )

        try:

            self._session_source = (
                self.microphone.__enter__()
            )

            self._session_active = True
            self._calibrated = False

            self._device_error_count = 0

            print(
                "Vyom : Microphone ready "
                "(adaptive mode)",
                flush=True
            )

            self._log(
                "Microphone session ACTIVE."
            )

            return True

        except Exception as error:

            self._device_error_count += 1

            self._log(
                "Microphone start failed: "
                + str(error)
            )

            self._reset_audio_device()

            return False

    # ---------------------------------------------------------
    # Stop Persistent Session
    # ---------------------------------------------------------

    def stop_session(self):

        self._log(
            "Stopping microphone session..."
        )

        self._close_microphone()

        self._session_active = False
        self._calibrated = False

        self._log(
            "Microphone session stopped."
        )

    # ---------------------------------------------------------
    # Wake Word Normalization
    # ---------------------------------------------------------

    def _normalize_wake_text(self, text):

        value = str(text or "").lower().strip()

        value = re.sub(
            r"[^\w\s\u0900-\u097F]",
            " ",
            value,
            flags=re.UNICODE
        )

        value = re.sub(
            r"\s+",
            " ",
            value
        )

        return value.strip()

    # ---------------------------------------------------------
    # Wake Word Detection
    # ---------------------------------------------------------

    def _looks_like_vyom(self, text):

        value = self._normalize_wake_text(text)

        if not value:
            return False

        wake_words = (
            "vyom",
            "व्योम",
            "व्योम जी",
            "hey vyom",
            "हे व्योम",
            "hey व्योम",
            "हे vyom"
        )

        for wake_word in wake_words:

            normalized = self._normalize_wake_text(
                wake_word
            )

            if value == normalized:
                return True

            if normalized in value:
                return True

        return False

    # ---------------------------------------------------------
    # Google Recognition
    # ---------------------------------------------------------

    def _recognize_google(self, audio, language):

        if self.recognizer is None:
            raise RuntimeError(
                "Speech recognizer is not initialized."
            )

        # Re-apply timeout before every request.
        #
        # This is intentionally done here because this is the
        # exact point where the network recognition starts.
        try:
            self.recognizer.operation_timeout = (
                self.google_request_timeout
            )
        except Exception:
            pass

        return self.recognizer.recognize_google(
            audio,
            language=language
        )

    # ---------------------------------------------------------
    # Recognition With Language Fallback
    # ---------------------------------------------------------

    def _recognize_with_fallback(
        self,
        audio,
        wake_mode=False
    ):

        if audio is None:

            return {
                "success": False,
                "text": "",
                "language": "",
                "status": "no_audio",
                "message": "No audio supplied."
            }

        languages = []

        if self.preferred_language:
            languages.append(
                self.preferred_language
            )

        if (
            self.fallback_language
            and self.fallback_language
            not in languages
        ):
            languages.append(
                self.fallback_language
            )

        if not languages:

            return {
                "success": False,
                "text": "",
                "language": "",
                "status": "no_language",
                "message": "No recognition language configured."
            }

        results = []

        for language in languages:

            self._log(
                "STT request started: "
                + str(language)
            )

            request_start = time.time()

            try:

                text = self._recognize_google(
                    audio,
                    language
                )

                elapsed = (
                    time.time()
                    - request_start
                )

                text = str(
                    text or ""
                ).strip()

                self._log(
                    "STT request finished: "
                    + str(language)
                    + " in "
                    + "{:.2f}".format(elapsed)
                    + "s"
                )

                if not text:
                    self._log(
                        "STT returned empty text: "
                        + str(language)
                    )
                    continue

                self._log(
                    "STT result ["
                    + str(language)
                    + "]: "
                    + text
                )

                results.append(
                    (
                        language,
                        text
                    )
                )

                self._last_text = text
                self._last_language = language

                # Normal command mode:
                # first successful recognition wins.
                if not wake_mode:

                    self._last_status = (
                        "recognized"
                    )

                    return {
                        "success": True,
                        "text": text,
                        "language": language,
                        "status": "recognized"
                    }

                # Wake-word mode:
                # only activate if Vyom is present.
                if self._looks_like_vyom(text):

                    self._last_status = (
                        "wake_detected"
                    )

                    return {
                        "success": True,
                        "text": text,
                        "language": language,
                        "status": "wake_detected"
                    }

                # Recognition worked, but wake word was not
                # present. Continue trying fallback language.
                self._log(
                    "Wake word not detected in "
                    + str(language)
                    + " result."
                )

            except Exception as error:

                self._recognition_error_count += 1

                message = str(error)
                lower = message.lower()

                # -----------------------------------------
                # No speech / unknown speech
                # -----------------------------------------

                if (
                    "unknownvalue" in lower
                    or "could not understand" in lower
                    or "unknown value" in lower
                ):

                    self._log(
                        "Speech not understood ["
                        + str(language)
                        + "]"
                    )

                    continue

                # -----------------------------------------
                # Network / Google service errors
                # -----------------------------------------

                if self._is_network_error(error):

                    self._log(
                        "STT network/service error ["
                        + str(language)
                        + "]: "
                        + message
                    )

                    # Do NOT crash the voice loop.
                    # Try fallback language if configured.
                    continue

                # -----------------------------------------
                # Microphone/device errors
                # -----------------------------------------

                if self._is_device_error(error):

                    self._log(
                        "STT device error during "
                        "recognition ["
                        + str(language)
                        + "]: "
                        + message
                    )

                    self._reset_audio_device()

                    return {
                        "success": False,
                        "text": "",
                        "language": "",
                        "status": "device_error",
                        "message": message
                    }

                # -----------------------------------------
                # Timeout / generic recognition error
                # -----------------------------------------

                if (
                    "timeout" in lower
                    or "timed out" in lower
                ):

                    self._log(
                        "STT recognition timeout ["
                        + str(language)
                        + "]"
                    )

                    continue

                # -----------------------------------------
                # Unknown error
                # -----------------------------------------

                self._log(
                    "Recognition error ["
                    + str(language)
                    + "]: "
                    + message
                )

                # Continue fallback instead of crashing.
                continue

        # -------------------------------------------------
        # Final result
        # -------------------------------------------------

        if wake_mode:

            if results:

                self._last_status = (
                    "wake_not_detected"
                )

                return {
                    "success": False,
                    "text": "",
                    "language": "",
                    "status": "wake_not_detected"
                }

            self._last_status = (
                "unrecognized"
            )

            return {
                "success": False,
                "text": "",
                "language": "",
                "status": "unrecognized"
            }

        self._last_status = (
            "unrecognized"
        )

        return {
            "success": False,
            "text": "",
            "language": "",
            "status": "unrecognized"
        }

    # ---------------------------------------------------------
    # Safe Microphone Timeout
    # ---------------------------------------------------------

    def _safe_timeout(self, timeout):

        try:

            value = float(timeout)

            if value <= 0:
                return None

            return value

        except (
            TypeError,
            ValueError
        ):

            return self.recognition_timeout

    # ---------------------------------------------------------
    # Safe Phrase Limit
    # ---------------------------------------------------------

    def _safe_phrase_limit(
        self,
        phrase_time_limit
    ):

        try:

            value = float(
                phrase_time_limit
            )

            if value <= 0:
                return None

            return value

        except (
            TypeError,
            ValueError
        ):

            return None

    # ---------------------------------------------------------
    # Listen
    # ---------------------------------------------------------

    def listen(
        self,
        timeout=5,
        phrase_time_limit=8,
        announce=True,
        wake_mode=None
    ):

        # ---------------------------------------------
        # Availability check
        # ---------------------------------------------

        if not self.available:

            return {
                "success": False,
                "text": "",
                "language": "",
                "status": "unavailable",
                "message": self.error_message
            }

        # ---------------------------------------------
        # Determine mode
        # ---------------------------------------------

        if wake_mode is None:

            # Existing API compatibility:
            # announce=False -> wake mode
            wake_mode = not bool(announce)

        source = None
        temporary_source = False

        try:

            # -----------------------------------------
            # Persistent microphone
            # -----------------------------------------

            if self._session_active:

                source = self._session_source

            else:

                self._log(
                    "Opening temporary microphone..."
                )

                source = (
                    self.microphone.__enter__()
                )

                temporary_source = True

            # -----------------------------------------
            # User-facing state
            # -----------------------------------------

            if wake_mode:

                print(
                    "Vyom : Listening for wake word...",
                    flush=True
                )

            else:

                print(
                    "Vyom : Listening...",
                    flush=True
                )

            self._log(
                "Waiting for speech..."
            )

            # -----------------------------------------
            # Microphone timeout
            # -----------------------------------------

            safe_timeout = (
                self._safe_timeout(timeout)
            )

            safe_phrase_limit = (
                self._safe_phrase_limit(
                    phrase_time_limit
                )
            )

            # -----------------------------------------
            # Audio capture
            # -----------------------------------------

            try:

                audio = self.recognizer.listen(
                    source,
                    timeout=safe_timeout,
                    phrase_time_limit=safe_phrase_limit
                )

            except Exception as error:

                # -------------------------------------
                # Device error
                # -------------------------------------

                if self._is_device_error(error):

                    self._device_error_count += 1

                    self._log(
                        "Audio capture device error: "
                        + str(error)
                    )

                    self._reset_audio_device()

                    return {
                        "success": False,
                        "text": "",
                        "language": "",
                        "status": "device_error",
                        "message": str(error)
                    }

                # -------------------------------------
                # Silence / microphone timeout
                # -------------------------------------

                message = str(
                    error
                ).lower()

                if (
                    "waittimeout" in message
                    or "timed out" in message
                    or "timeout" in message
                ):

                    self._log(
                        "No speech detected."
                    )

                    return {
                        "success": False,
                        "text": "",
                        "language": "",
                        "status": "silence",
                        "message": "No speech detected."
                    }

                # -------------------------------------
                # Other capture error
                # -------------------------------------

                raise

            # -----------------------------------------
            # No audio
            # -----------------------------------------

            if audio is None:

                self._log(
                    "Audio capture returned nothing."
                )

                return {
                    "success": False,
                    "text": "",
                    "language": "",
                    "status": "no_audio",
                    "message": "No audio captured."
                }

            # -----------------------------------------
            # Audio captured
            # -----------------------------------------

            print(
                "Vyom : Audio captured. "
                "Processing speech...",
                flush=True
            )

            self._log(
                "Audio capture COMPLETE."
            )

            # -----------------------------------------
            # Recognition
            # -----------------------------------------

            recognition_start = time.time()

            result = (
                self._recognize_with_fallback(
                    audio,
                    wake_mode=wake_mode
                )
            )

            recognition_elapsed = (
                time.time()
                - recognition_start
            )

            self._log(
                "Recognition stage completed in "
                + "{:.2f}".format(
                    recognition_elapsed
                )
                + "s"
            )

            # -----------------------------------------
            # Store result
            # -----------------------------------------

            self._last_text = (
                result.get("text", "")
            )

            self._last_language = (
                result.get("language", "")
            )

            self._last_status = (
                result.get("status", "")
            )

            # -----------------------------------------
            # User-facing result
            # -----------------------------------------

            if result.get("success"):

                print(
                    "You : "
                    + result.get(
                        "text",
                        ""
                    ),
                    flush=True
                )

            else:

                self._log(
                    "Recognition status: "
                    + str(
                        result.get(
                            "status",
                            ""
                        )
                    )
                )

            return result

        # -------------------------------------------------
        # Outer safety layer
        # -------------------------------------------------

        except Exception as error:

            # Device error
            if self._is_device_error(error):

                self._device_error_count += 1

                self._log(
                    "Microphone device error: "
                    + str(error)
                )

                self._reset_audio_device()

                return {
                    "success": False,
                    "text": "",
                    "language": "",
                    "status": "device_error",
                    "message": str(error)
                }

            # Network errors must never crash the loop.
            if self._is_network_error(error):

                self._log(
                    "STT network error: "
                    + str(error)
                )

                return {
                    "success": False,
                    "text": "",
                    "language": "",
                    "status": "network_error",
                    "message": str(error)
                }

            # Generic STT error.
            self._log(
                "STT listen error: "
                + str(error)
            )

            return {
                "success": False,
                "text": "",
                "language": "",
                "status": "error",
                "message": str(error)
            }

        # -------------------------------------------------
        # Temporary microphone cleanup
        # -------------------------------------------------

        finally:

            if (
                temporary_source
                and source is not None
            ):

                try:

                    source.__exit__(
                        None,
                        None,
                        None
                    )

                except Exception:
                    pass

    # ---------------------------------------------------------
    # Backward Compatible listen_once()
    # ---------------------------------------------------------

    def listen_once(
        self,
        timeout=5,
        phrase_time_limit=8,
        announce=True
    ):

        return self.listen(
            timeout=timeout,
            phrase_time_limit=phrase_time_limit,
            announce=announce,
            wake_mode=not bool(announce)
        )

    # ---------------------------------------------------------
    # Recognize Existing Audio
    # ---------------------------------------------------------

    def recognize(self, audio):

        return self._recognize_with_fallback(
            audio,
            wake_mode=False
        )

    # ---------------------------------------------------------
    # Test
    # ---------------------------------------------------------

    def test(self):

        print("=" * 60)

        print(
            "Vyom AI - Speech To Text Test v1.1"
        )

        print("=" * 60)

        print("")

        if not self.available:

            print(
                "STT Status : NOT AVAILABLE"
            )

            print(
                "Reason : "
                + self.error_message
            )

            return

        print(
            "STT Status : READY"
        )

        print(
            "Preferred Language : "
            + str(
                self.preferred_language
            )
        )

        print(
            "Fallback Language : "
            + str(
                self.fallback_language
            )
        )

        print(
            "Google Request Timeout : "
            + str(
                self.google_request_timeout
            )
            + " seconds"
        )

        print("")

        if not self.start_session():

            print(
                "Microphone Status : FAILED"
            )

            return

        try:

            result = self.listen(
                timeout=5,
                phrase_time_limit=8,
                announce=True,
                wake_mode=False
            )

            print("")

            print(
                "Result : "
                + str(result)
            )

        finally:

            self.stop_session()


# -------------------------------------------------------------
# Standalone Test Entry
# -------------------------------------------------------------

def main():

    stt = SpeechToText(
        preferred_language="hi-IN",
        fallback_language="en-IN",
        debug=True
    )

    stt.test()


if __name__ == "__main__":
    main()
