"""
Project : Vyom AI
Version : 0.7
Module  : Speech To Text

Purpose:
    Convert microphone speech into text.

Windows 8 Friendly:
    - Uses SpeechRecognition.
    - Uses a persistent microphone only during active voice session.
    - Explicit audio-stage diagnostics.
    - Hindi -> English fallback.
    - Wake-word mode and normal command mode are separated.
    - Handles old/unstable audio devices gracefully.

IMPORTANT:
    This module only captures and recognizes speech.
    It does not execute commands.
"""

import re
import time


class SpeechToText:

    # =========================================================
    # INITIALIZATION
    # =========================================================

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

        self.preferred_language = (
            preferred_language
        )

        self.fallback_language = (
            fallback_language
        )

        self._session_active = False

        self._session_source = None

        self._calibrated = False

        self._last_text = ""

        self._last_language = ""

        self._last_status = ""

        self._device_error_count = 0

        self._initialize()

    # =========================================================
    # AUDIO SETTINGS
    # =========================================================

    recognition_timeout = 4

    initial_energy_threshold = 250

    dynamic_energy_adjustment_damping = 0.15

    dynamic_energy_ratio = 1.5

    pause_threshold = 0.65

    non_speaking_duration = 0.35

    phrase_threshold = 0.20

    # =========================================================
    # DEBUG
    # =========================================================

    def _log(self, message):

        if not self.debug:
            return

        try:
            print(
                "[STT] " + str(message),
                flush=True
            )
        except Exception:
            pass

    # =========================================================
    # INITIALIZE
    # =========================================================

    def _initialize(self):

        self._log(
            "Initializing Speech-To-Text..."
        )

        try:

            import speech_recognition as sr

            self._log(
                "speech_recognition import: OK"
            )

            self.recognizer = sr.Recognizer()

            self.recognizer.pause_threshold = (
                self.pause_threshold
            )

            self.recognizer.non_speaking_duration = (
                self.non_speaking_duration
            )

            self.recognizer.phrase_threshold = (
                self.phrase_threshold
            )

            self.recognizer.dynamic_energy_threshold = True

            self.recognizer.energy_threshold = (
                self.initial_energy_threshold
            )

            try:

                self.recognizer.dynamic_energy_adjustment_damping = (
                    self.dynamic_energy_adjustment_damping
                )

                self.recognizer.dynamic_energy_ratio = (
                    self.dynamic_energy_ratio
                )

            except Exception:
                pass

            try:

                self.recognizer.operation_timeout = 10

            except Exception:
                pass

            self._log(
                "Checking microphone..."
            )

            self.microphone = sr.Microphone()

            self.available = True

            self.error_message = ""

            self._log(
                "Speech-To-Text READY."
            )

        except Exception as error:

            self.available = False

            self.error_message = str(
                error
            )

            self._log(
                "STT initialization failed: "
                + self.error_message
            )

    # =========================================================
    # STATUS
    # =========================================================

    def is_available(self):

        return self.available

    # =========================================================
    # DEVICE ERROR
    # =========================================================

    def _is_device_error(
        self,
        error
    ):

        message = str(
            error or ""
        ).lower()

        patterns = (
            "winerror 31",
            "device attached",
            "no default input device",
            "invalid input device",
            "input device",
            "permissionerror",
            "audio device",
            "paerror",
            "portaudio"
        )

        return any(
            pattern in message
            for pattern in patterns
        )

    # =========================================================
    # RESET DEVICE
    # =========================================================

    def _reset_audio_device(self):

        self._log(
            "Resetting microphone state..."
        )

        self._close_microphone()

        self._session_active = False

        self._session_source = None

        self._calibrated = False

        time.sleep(
            0.25
        )

    # =========================================================
    # CLOSE MICROPHONE
    # =========================================================

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

    # =========================================================
    # START SESSION
    # =========================================================

    def start_session(self):

        if not self.available:

            self._log(
                "Cannot start session: STT unavailable."
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
                "Vyom : Microphone ready (adaptive mode)",
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

    # =========================================================
    # STOP SESSION
    # =========================================================

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

    # =========================================================
    # NORMALIZE WAKE TEXT
    # =========================================================

    def _normalize_wake_text(
        self,
        text
    ):

        value = str(
            text or ""
        ).lower().strip()

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

        return value

    # =========================================================
    # WAKE WORD CHECK
    # =========================================================

    def _looks_like_vyom(
        self,
        text
    ):

        value = self._normalize_wake_text(
            text
        )

        if not value:
            return False

        wake_words = (
            "vyom",
            "व्योम",
            "व्योम जी",
            "hey vyom",
            "हे व्योम"
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

    # =========================================================
    # GOOGLE RECOGNITION
    # =========================================================

    def _recognize_google(
        self,
        audio,
        language
    ):

        return self.recognizer.recognize_google(
            audio,
            language=language
        )

    # =========================================================
    # RECOGNIZE WITH FALLBACK
    # =========================================================

    def _recognize_with_fallback(
        self,
        audio,
        wake_mode=False
    ):

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

        results = []

        for language in languages:

            self._log(
                "STT request started: "
                + str(language)
            )

            try:

                text = self._recognize_google(
                    audio,
                    language
                )

                text = str(
                    text or ""
                ).strip()

                if not text:
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

                # -------------------------------------------------
                # Normal command mode
                # -------------------------------------------------

                if not wake_mode:

                    return {
                        "success": True,
                        "text": text,
                        "language": language,
                        "status": "recognized"
                    }

                # -------------------------------------------------
                # Wake mode
                # -------------------------------------------------

                if self._looks_like_vyom(
                    text
                ):

                    return {
                        "success": True,
                        "text": text,
                        "language": language,
                        "status": "wake_detected"
                    }

            except Exception as error:

                message = str(
                    error
                )

                lower = message.lower()

                if (
                    "requesterror" in lower
                    or "connection" in lower
                    or "network" in lower
                    or "recognition connection" in lower
                ):

                    self._log(
                        "STT service error ["
                        + str(language)
                        + "]: "
                        + message
                    )

                    continue

                if (
                    "unknownvalue" in lower
                    or "could not understand" in lower
                ):

                    continue

                self._log(
                    "Recognition error ["
                    + str(language)
                    + "]: "
                    + message
                )

                continue

        if wake_mode and results:

            return {
                "success": False,
                "text": "",
                "language": "",
                "status": "wake_not_detected"
            }

        return {
            "success": False,
            "text": "",
            "language": "",
            "status": "unrecognized"
        }

    # =========================================================
    # SAFE TIMEOUT
    # =========================================================

    def _safe_timeout(
        self,
        timeout
    ):

        try:

            value = float(
                timeout
            )

            if value <= 0:
                return None

            return value

        except (
            TypeError,
            ValueError
        ):

            return self.recognition_timeout

    # =========================================================
    # SAFE PHRASE LIMIT
    # =========================================================

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

    # =========================================================
    # LISTEN
    # =========================================================

    def listen(
        self,
        timeout=5,
        phrase_time_limit=8,
        announce=True,
        wake_mode=None
    ):

        if not self.available:

            return {
                "success": False,
                "text": "",
                "language": "",
                "status": "unavailable",
                "message": self.error_message
            }

        if wake_mode is None:

            wake_mode = not bool(
                announce
            )

        source = None

        temporary_source = False

        try:

            # -----------------------------------------------------
            # Persistent microphone
            # -----------------------------------------------------

            if self._session_active:

                source = self._session_source

            # -----------------------------------------------------
            # Temporary microphone
            # -----------------------------------------------------

            else:

                self._log(
                    "Opening temporary microphone..."
                )

                source = (
                    self.microphone.__enter__()
                )

                temporary_source = True

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

            safe_timeout = self._safe_timeout(
                timeout
            )

            safe_phrase_limit = (
                self._safe_phrase_limit(
                    phrase_time_limit
                )
            )

            try:

                audio = self.recognizer.listen(
                    source,
                    timeout=safe_timeout,
                    phrase_time_limit=safe_phrase_limit
                )

            except Exception as error:

                if self._is_device_error(
                    error
                ):

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

                # Wait timeout is intentionally handled
                # without killing the voice loop.

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

                raise

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

            print(
                "Vyom : Audio captured. Processing speech...",
                flush=True
            )

            self._log(
                "Audio capture COMPLETE."
            )

            # -----------------------------------------------------
            # Recognition
            # -----------------------------------------------------

            result = self._recognize_with_fallback(
                audio,
                wake_mode=wake_mode
            )

            self._last_text = result.get(
                "text",
                ""
            )

            self._last_language = result.get(
                "language",
                ""
            )

            self._last_status = result.get(
                "status",
                ""
            )

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

        except Exception as error:

            if self._is_device_error(
                error
            ):

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

        finally:

            if temporary_source and source is not None:

                try:

                    source.__exit__(
                        None,
                        None,
                        None
                    )

                except Exception:
                    pass

    # =========================================================
    # LISTEN ONCE
    # =========================================================

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
            wake_mode=not bool(
                announce
            )
        )

    # =========================================================
    # RECOGNIZE
    # =========================================================

    def recognize(
        self,
        audio
    ):

        return self._recognize_with_fallback(
            audio,
            wake_mode=False
        )

    # =========================================================
    # TEST
    # =========================================================

    def test(self):

        print(
            "=" * 60
        )

        print(
            "Vyom AI - Speech To Text Test v0.7"
        )

        print(
            "=" * 60
        )

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


# =============================================================
# STANDALONE TEST
# =============================================================

def main():

    stt = SpeechToText(
        debug=True
    )

    stt.test()


if __name__ == "__main__":

    main()
