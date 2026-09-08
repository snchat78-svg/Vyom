"""Vyom AI - robust Speech-To-Text and microphone session layer.

Architecture:
    microphone -> audio capture -> Google STT -> structured result

VoiceController owns conversation/wake/session policy.  This module owns
only microphone capture and speech recognition.

Important design choice:
    Wake-word recognition uses a normal string transcript request rather than
    ``show_all=True``.  This keeps the recognition path deterministic and
    compatible with older SpeechRecognition installations.  Wake aliases and
    fuzzy matching are evaluated locally after transcription.
"""

import re
import time


class SpeechToText:
    """Persistent microphone + Google SpeechRecognition boundary."""

    recognition_timeout = 4
    google_request_timeout = 5

    initial_energy_threshold = 250
    dynamic_energy_adjustment_damping = 0.15
    dynamic_energy_ratio = 1.5

    # Short pause threshold helps short commands/wake phrases without making
    # normal speech too fragmented.
    pause_threshold = 0.65
    non_speaking_duration = 0.35
    phrase_threshold = 0.20

    recovery_delay = 0.35

    # Wake recognition is intentionally tried in English first because the
    # wake word is a Latin proper name and Google often transliterates it more
    # reliably there.  Hindi remains the fallback for Hindi-only recognition.
    wake_languages = ("en-IN", "hi-IN")

    def __init__(self, preferred_language="hi-IN", fallback_language="en-IN", debug=True):
        self.recognizer = None
        self.microphone = None
        self.available = False
        self.error_message = ""
        self.debug = bool(debug)

        self.preferred_language = preferred_language or "hi-IN"
        self.fallback_language = fallback_language or "en-IN"

        self._session_active = False
        self._session_source = None

        self._last_text = ""
        self._last_language = ""
        self._last_status = ""

        self._device_error_count = 0
        self._recognition_error_count = 0
        self._sr_module = None

        self._initialize()

    # ------------------------------------------------------------------
    # Logging
    # ------------------------------------------------------------------

    def _log(self, message):
        if not self.debug:
            return
        try:
            print("[STT] " + str(message), flush=True)
        except Exception:
            pass

    # ------------------------------------------------------------------
    # Initialization
    # ------------------------------------------------------------------

    def _initialize(self):
        self._log("Initializing Speech-To-Text...")
        try:
            import speech_recognition as sr

            self._sr_module = sr
            self._log("speech_recognition import: OK")

            self.recognizer = sr.Recognizer()
            self.recognizer.pause_threshold = self.pause_threshold
            self.recognizer.non_speaking_duration = self.non_speaking_duration
            self.recognizer.phrase_threshold = self.phrase_threshold
            self.recognizer.dynamic_energy_threshold = True
            self.recognizer.energy_threshold = self.initial_energy_threshold
            self.recognizer.dynamic_energy_adjustment_damping = (
                self.dynamic_energy_adjustment_damping
            )
            self.recognizer.dynamic_energy_ratio = self.dynamic_energy_ratio
            self.recognizer.operation_timeout = self.google_request_timeout

            self._log(
                "Google recognition timeout: %s seconds" % self.google_request_timeout
            )
            self._log("Checking microphone...")

            self.microphone = sr.Microphone()
            self.available = True
            self.error_message = ""
            self._log("Speech-To-Text READY.")

        except Exception as error:
            self.available = False
            self.error_message = str(error)
            self._log("STT initialization failed: " + self.error_message)

    def is_available(self):
        return bool(self.available)

    # ------------------------------------------------------------------
    # Error classification
    # ------------------------------------------------------------------

    @staticmethod
    def _lower(error):
        return str(error or "").lower()

    def _is_device_error(self, error):
        text = self._lower(error)
        return any(token in text for token in (
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
            "microphone",
        ))

    def _is_network_error(self, error):
        text = self._lower(error)
        return any(token in text for token in (
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
            "temporary failure",
        ))

    @staticmethod
    def _is_unknown_speech(error):
        text = str(error or "").lower()
        return (
            "unknownvalue" in text
            or "unknown value" in text
            or "could not understand" in text
            or "couldn't understand" in text
        )

    # ------------------------------------------------------------------
    # Microphone lifecycle
    # ------------------------------------------------------------------

    def _close_microphone(self):
        source = self._session_source
        self._session_source = None
        if source is not None:
            try:
                source.__exit__(None, None, None)
            except Exception:
                pass

    def _reset_audio_device(self):
        self._log("Resetting microphone state...")
        self._close_microphone()
        self._session_active = False
        try:
            time.sleep(self.recovery_delay)
        except Exception:
            pass

    def start_session(self):
        if not self.available or self.microphone is None:
            return False

        if self._session_active:
            return True

        self._log("Opening microphone session...")
        try:
            self._session_source = self.microphone.__enter__()
            self._session_active = True
            self._device_error_count = 0
            print("Vyom : Microphone ready (adaptive mode)", flush=True)
            self._log("Microphone session ACTIVE.")
            return True
        except Exception as error:
            self._device_error_count += 1
            self._log("Microphone start failed: " + str(error))
            self._reset_audio_device()
            return False

    def stop_session(self):
        self._log("Stopping microphone session...")
        self._close_microphone()
        self._session_active = False
        self._log("Microphone session stopped.")

    def recover_session(self):
        self._log("Recovery start.")
        self._reset_audio_device()

        try:
            if self.start_session():
                self._log("Microphone session restored.")
                return True
        except Exception as error:
            self._log("Existing microphone recovery failed: " + str(error))

        self._log("Reinitializing Speech-To-Text...")
        self._initialize()
        if not self.available:
            self._log("STT reinitialization failed.")
            return False

        try:
            restored = self.start_session()
            if restored:
                self._log("Microphone session restored after reinitialization.")
            return restored
        except Exception as error:
            self._log("Microphone recovery failed: " + str(error))
            return False

    # ------------------------------------------------------------------
    # Safe time values
    # ------------------------------------------------------------------

    def _safe_timeout(self, timeout):
        try:
            value = float(timeout)
            return value if value > 0 else None
        except (TypeError, ValueError):
            return float(self.recognition_timeout)

    @staticmethod
    def _safe_phrase_limit(value):
        try:
            number = float(value)
            return number if number > 0 else None
        except (TypeError, ValueError):
            return None

    # ------------------------------------------------------------------
    # Google recognition
    # ------------------------------------------------------------------

    def _recognize_google(self, audio, language):
        if self.recognizer is None:
            raise RuntimeError("Speech recognizer is not initialized.")

        # SpeechRecognition uses this timeout for its internal network/API
        # request.  Re-apply it immediately before every call.
        self.recognizer.operation_timeout = self.google_request_timeout
        return self.recognizer.recognize_google(audio, language=language)

    def _recognize_one(self, audio, language, label="STT"):
        started = time.time()
        self._log("%s request started: %s" % (label, language))
        try:
            text = str(self._recognize_google(audio, language) or "").strip()
            elapsed = time.time() - started
            self._log(
                "%s request finished: %s in %.2fs"
                % (label, language, elapsed)
            )
            self._log("%s transcript: %s" % (label, text if text else "<empty>"))
            return {
                "success": bool(text),
                "text": text,
                "language": language,
                "status": "recognized" if text else "unrecognized",
            }
        except Exception as error:
            elapsed = time.time() - started
            self._recognition_error_count += 1
            message = str(error)
            self._log(
                "%s request error: %s after %.2fs"
                % (label, message, elapsed)
            )

            if self._is_device_error(error):
                self._device_error_count += 1
                self._reset_audio_device()
                return {
                    "success": False,
                    "text": "",
                    "language": "",
                    "status": "device_error",
                    "message": message,
                }

            if self._is_unknown_speech(error):
                return {
                    "success": False,
                    "text": "",
                    "language": language,
                    "status": "unrecognized",
                    "message": message,
                }

            if self._is_network_error(error):
                return {
                    "success": False,
                    "text": "",
                    "language": language,
                    "status": "network_error",
                    "message": message,
                }

            return {
                "success": False,
                "text": "",
                "language": language,
                "status": "recognition_error",
                "message": message,
            }

    # ------------------------------------------------------------------
    # Wake matching
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_text(text):
        value = str(text or "").lower().strip()
        value = re.sub(r"[^\w\s\u0900-\u097F]", " ", value, flags=re.UNICODE)
        return re.sub(r"\s+", " ", value).strip()

    @staticmethod
    def _compact(text):
        return re.sub(r"\s+", "", SpeechToText._normalize_text(text))

    def _wake_aliases(self):
        # Common English, Hindi transliteration and Google misrecognitions.
        return (
            "vyom",
            "viyom",
            "viom",
            "vyam",
            "veom",
            "vyoam",
            "viyam",
            "biom",
            "व्योम",
            "वियोम",
            "वियॉम",
            "वियम",
            "व्यम",
            "ब्योम",
            "बायोम",
            "व्योम जी",
            "व्योमजी",
            "व्योम जि",
            "hey vyom",
            "hey vयom",
            "हे व्योम",
            "हे वियोम",
        )

    def _wake_detected(self, text):
        value = self._normalize_text(text)
        if not value:
            return False, ""

        compact_value = self._compact(value)
        aliases = self._wake_aliases()

        normalized_aliases = []
        for alias in aliases:
            norm = self._normalize_text(alias)
            if norm and norm not in normalized_aliases:
                normalized_aliases.append(norm)

        # Exact phrase / token containment first.
        for alias in normalized_aliases:
            if value == alias or alias in value or self._compact(alias) in compact_value:
                return True, alias

        # Google can produce a short phonetic variant.  Fuzzy matching is
        # limited to short utterances to prevent false activation on normal
        # sentences.
        if len(value) <= 24:
            try:
                import difflib
                best_alias = ""
                best_score = 0.0
                for alias in normalized_aliases:
                    if len(alias) > 12:
                        continue
                    score = difflib.SequenceMatcher(None, compact_value, self._compact(alias)).ratio()
                    if score > best_score:
                        best_score = score
                        best_alias = alias
                if best_score >= 0.72:
                    return True, best_alias
            except Exception:
                pass

        return False, ""

    def _recognize_wake(self, audio):
        """Recognize wake speech and return an explicit wake_detected result."""
        languages = []
        for language in self.wake_languages:
            if language and language not in languages:
                languages.append(language)
        # Keep configured languages available as a final compatibility pair.
        for language in (self.preferred_language, self.fallback_language):
            if language and language not in languages:
                languages.append(language)

        any_transcript = ""
        any_language = ""
        last_error = ""

        self._log("WAKE recognition cycle START")

        for language in languages:
            result = self._recognize_one(audio, language, label="WAKE STT")

            if result.get("status") == "device_error":
                self._last_status = "device_error"
                return result

            text = str(result.get("text") or "").strip()
            if text:
                any_transcript = text
                any_language = language
                matched, alias = self._wake_detected(text)
                if matched:
                    self._last_text = text
                    self._last_language = language
                    self._last_status = "wake_detected"
                    self._log("WAKE WORD MATCHED: " + alias)
                    self._log("WAKE recognition cycle END: wake_detected")
                    return {
                        "success": True,
                        "text": text,
                        "language": language,
                        "status": "wake_detected",
                        "wake_word": alias,
                    }
                self._log("Wake not present in %s transcript." % language)

            if result.get("message"):
                last_error = str(result.get("message"))

        status = "wake_not_detected" if any_transcript else "unrecognized"
        self._last_text = any_transcript
        self._last_language = any_language
        self._last_status = status

        self._log("WAKE recognition cycle END: " + status)
        return {
            "success": False,
            "text": any_transcript,
            "language": any_language,
            "status": status,
            "message": last_error,
        }

    def _recognize_command(self, audio):
        languages = []
        for language in (self.preferred_language, self.fallback_language):
            if language and language not in languages:
                languages.append(language)

        last_error = ""
        for language in languages:
            result = self._recognize_one(audio, language, label="STT")

            if result.get("status") == "device_error":
                return result

            if result.get("success"):
                self._last_text = result.get("text", "")
                self._last_language = language
                self._last_status = "recognized"
                return result

            last_error = str(result.get("message", "") or "")

        self._last_status = "unrecognized"
        return {
            "success": False,
            "text": "",
            "language": "",
            "status": "unrecognized",
            "message": last_error,
        }

    # ------------------------------------------------------------------
    # Main listen API
    # ------------------------------------------------------------------

    def listen(self, timeout=5, phrase_time_limit=8, announce=True, wake_mode=None):
        if not self.available:
            return {
                "success": False,
                "text": "",
                "language": "",
                "status": "unavailable",
                "message": self.error_message,
            }

        if wake_mode is None:
            wake_mode = not bool(announce)

        source = self._session_source
        temporary = False

        try:
            if not self._session_active:
                source = self.microphone.__enter__()
                temporary = True

            print(
                "Vyom : Listening for wake word..." if wake_mode else "Vyom : Listening...",
                flush=True,
            )
            self._log("Waiting for speech...")

            audio = self.recognizer.listen(
                source,
                timeout=self._safe_timeout(timeout),
                phrase_time_limit=self._safe_phrase_limit(phrase_time_limit),
            )

            if audio is None:
                result = {
                    "success": False,
                    "text": "",
                    "language": "",
                    "status": "no_audio",
                    "message": "No audio captured.",
                }
                self._last_status = "no_audio"
                return result

            print("Vyom : Audio captured. Processing speech...", flush=True)
            self._log("Audio capture COMPLETE.")

            result = self._recognize_wake(audio) if wake_mode else self._recognize_command(audio)

            if result.get("success"):
                print("You : " + str(result.get("text", "")), flush=True)
            else:
                self._log("Recognition status: " + str(result.get("status", "")))

            return result

        except Exception as error:
            if self._is_device_error(error):
                self._device_error_count += 1
                self._reset_audio_device()
                return {
                    "success": False,
                    "text": "",
                    "language": "",
                    "status": "device_error",
                    "message": str(error),
                }

            message = str(error).lower()
            if "waittimeout" in message or "timed out" in message or "timeout" in message:
                self._last_status = "silence"
                self._log("No speech detected.")
                return {
                    "success": False,
                    "text": "",
                    "language": "",
                    "status": "silence",
                    "message": "No speech detected.",
                }

            self._last_status = "error"
            self._log("STT listen error: " + str(error))
            return {
                "success": False,
                "text": "",
                "language": "",
                "status": "error",
                "message": str(error),
            }

        finally:
            if temporary and source is not None:
                try:
                    source.__exit__(None, None, None)
                except Exception:
                    pass

    def listen_once(self, timeout=5, phrase_time_limit=8, announce=True):
        return self.listen(
            timeout=timeout,
            phrase_time_limit=phrase_time_limit,
            announce=announce,
            wake_mode=not bool(announce),
        )

    def recognize(self, audio):
        return self._recognize_command(audio)

    def test(self):
        if not self.available:
            print("STT Status : NOT AVAILABLE")
            print("Reason : " + self.error_message)
            return

        print("STT Status : READY")
        if not self.start_session():
            return

        try:
            while True:
                result = self.listen(timeout=5, phrase_time_limit=8, announce=True, wake_mode=False)
                print(result)
                if result.get("text", "").strip().lower() in {"exit", "quit"}:
                    break
        finally:
            self.stop_session()


if __name__ == "__main__":
    SpeechToText().test()
