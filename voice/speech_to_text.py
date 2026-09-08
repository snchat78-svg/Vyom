"""Vyom AI - reliable speech-to-text boundary.

Design:
    logical voice session -> capture one utterance -> close microphone ->
    recognize -> return structured result.

The microphone is intentionally opened only for the short capture window.
Keeping a PyAudio/PortAudio input stream open while pyttsx3/SAPI speaks can
cause audio-device contention on older Windows systems.  The user still gets
continuous conversation because VoiceController manages the logical session;
there is no push-to-talk interaction.
"""

import difflib
import re
import time


class SpeechToText:
    recognition_timeout = 4
    google_request_timeout = 5

    initial_energy_threshold = 250
    dynamic_energy_adjustment_damping = 0.15
    dynamic_energy_ratio = 1.5

    pause_threshold = 0.65
    non_speaking_duration = 0.35
    phrase_threshold = 0.20

    recovery_delay = 0.35

    # English first: "Vyom" is a Latin proper name and Google often
    # transliterates it more reliably with en-IN.
    wake_languages = ("en-IN", "hi-IN")

    def __init__(self, preferred_language="hi-IN", fallback_language="en-IN", debug=True):
        self.recognizer = None
        self.microphone = None
        self.available = False
        self.error_message = ""
        self.debug = bool(debug)

        self.preferred_language = preferred_language or "hi-IN"
        self.fallback_language = fallback_language or "en-IN"

        # Logical session state.  The physical microphone context is NOT kept
        # open between utterances.
        self._session_active = False
        self._last_text = ""
        self._last_language = ""
        self._last_status = ""
        self._device_error_count = 0
        self._recognition_error_count = 0
        self._sr_module = None
        self._initialize()

    def _log(self, message):
        if not self.debug:
            return
        try:
            print("[STT] " + str(message), flush=True)
        except Exception:
            pass

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
            self.recognizer.dynamic_energy_adjustment_damping = self.dynamic_energy_adjustment_damping
            self.recognizer.dynamic_energy_ratio = self.dynamic_energy_ratio
            self.recognizer.operation_timeout = self.google_request_timeout

            self._log("Google recognition timeout: %s seconds" % self.google_request_timeout)
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

    @staticmethod
    def _lower(error):
        return str(error or "").lower()

    def _is_device_error(self, error):
        text = self._lower(error)
        return any(token in text for token in (
            "winerror 31", "device attached", "no default input device",
            "invalid input device", "input device", "permissionerror",
            "audio device", "paerror", "portaudio", "wasapi",
            "directsound", "mmdevice", "microphone",
        ))

    def _is_network_error(self, error):
        text = self._lower(error)
        return any(token in text for token in (
            "requesterror", "connection", "network", "urlopen",
            "timed out", "timeout", "service unavailable",
            "remote end closed", "connection reset", "connection aborted",
            "connection refused", "name or service not known",
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
    # Logical session lifecycle
    # ------------------------------------------------------------------

    def start_session(self):
        if not self.available or self.microphone is None:
            return False
        self._session_active = True
        self._device_error_count = 0
        print("Vyom : Microphone ready (adaptive mode)", flush=True)
        self._log("Logical microphone session ACTIVE (capture-per-utterance mode).")
        return True

    def stop_session(self):
        self._session_active = False
        self._log("Logical microphone session stopped.")

    def recover_session(self):
        self._log("Recovery start.")
        self._session_active = False
        try:
            time.sleep(self.recovery_delay)
        except Exception:
            pass
        if not self.available or self.microphone is None:
            self._initialize()
        if not self.available or self.microphone is None:
            self._log("Microphone recovery failed: STT unavailable.")
            return False
        self._session_active = True
        self._log("Microphone capture session restored.")
        return True

    # ------------------------------------------------------------------
    # Recognition
    # ------------------------------------------------------------------

    def _recognize_google(self, audio, language):
        if self.recognizer is None:
            raise RuntimeError("Speech recognizer is not initialized.")
        self.recognizer.operation_timeout = self.google_request_timeout
        return self.recognizer.recognize_google(audio, language=language)

    def _recognize_one(self, audio, language, label="STT"):
        started = time.time()
        self._log("%s request started: %s" % (label, language))
        try:
            text = str(self._recognize_google(audio, language) or "").strip()
            elapsed = time.time() - started
            self._log("%s request finished: %s in %.2fs" % (label, language, elapsed))
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
            self._log("%s request error: %s after %.2fs" % (label, message, elapsed))
            if self._is_device_error(error):
                self._device_error_count += 1
                return {
                    "success": False, "text": "", "language": "",
                    "status": "device_error", "message": message,
                }
            if self._is_unknown_speech(error):
                return {
                    "success": False, "text": "", "language": language,
                    "status": "unrecognized", "message": message,
                }
            if self._is_network_error(error):
                return {
                    "success": False, "text": "", "language": language,
                    "status": "network_error", "message": message,
                }
            return {
                "success": False, "text": "", "language": language,
                "status": "recognition_error", "message": message,
            }

    @staticmethod
    def _normalize_text(text):
        value = str(text or "").lower().strip()
        value = re.sub(r"[^\w\s\u0900-\u097F]", " ", value, flags=re.UNICODE)
        return re.sub(r"\s+", " ", value).strip()

    @staticmethod
    def _compact(text):
        return re.sub(r"\s+", "", SpeechToText._normalize_text(text))

    def _wake_aliases(self):
        return (
            "vyom", "viyom", "viom", "vyam", "veom", "vyoam", "viyam",
            "biom", "beyom", "vyoum", "व्योम", "वियोम", "वियॉम", "वियम",
            "व्यम", "ब्योम", "बायोम", "व्योम जी", "व्योमजी", "व्योम जि",
            "hey vyom", "हे व्योम", "हे वियोम",
        )

    def _wake_detected(self, text):
        value = self._normalize_text(text)
        if not value:
            return False, ""

        compact_value = self._compact(value)
        aliases = []
        for alias in self._wake_aliases():
            normalized = self._normalize_text(alias)
            if normalized and normalized not in aliases:
                aliases.append(normalized)

        for alias in aliases:
            if value == alias or alias in value or self._compact(alias) in compact_value:
                return True, alias

        # Only short transcripts are eligible for fuzzy wake matching.
        if len(value) <= 24:
            best_alias = ""
            best_score = 0.0
            for alias in aliases:
                if len(alias) > 12:
                    continue
                score = difflib.SequenceMatcher(None, compact_value, self._compact(alias)).ratio()
                if score > best_score:
                    best_score = score
                    best_alias = alias
            if best_score >= 0.72:
                return True, best_alias
        return False, ""

    def _recognize_wake(self, audio):
        languages = []
        for language in self.wake_languages + (self.preferred_language, self.fallback_language):
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
                        "success": True, "text": text, "language": language,
                        "status": "wake_detected", "wake_word": alias,
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
            "success": False, "text": any_transcript, "language": any_language,
            "status": status, "message": last_error,
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
            "success": False, "text": "", "language": "", "status": "unrecognized",
            "message": last_error,
        }

    # ------------------------------------------------------------------
    # Audio capture
    # ------------------------------------------------------------------

    def _capture(self, timeout, phrase_time_limit):
        if self.microphone is None or self.recognizer is None:
            raise RuntimeError("Microphone or recognizer is not initialized.")

        # Critical Windows design: the physical microphone context exists only
        # while listening. It is released BEFORE Google recognition or TTS.
        self._log("Opening microphone for one utterance...")
        with self.microphone as source:
            self._log("Waiting for speech...")
            audio = self.recognizer.listen(
                source,
                timeout=timeout,
                phrase_time_limit=phrase_time_limit,
            )
        self._log("Audio capture COMPLETE; microphone released.")
        return audio

    def listen(self, timeout=5, phrase_time_limit=8, announce=True, wake_mode=None):
        if not self.available:
            return {
                "success": False, "text": "", "language": "",
                "status": "unavailable", "message": self.error_message,
            }

        if wake_mode is None:
            wake_mode = not bool(announce)

        try:
            self._log(
                "CAPTURE START: mode=%s timeout=%s phrase_limit=%s session=%s"
                % ("WAKE" if wake_mode else "COMMAND", timeout, phrase_time_limit, self._session_active)
            )
            audio = self._capture(self._safe_timeout(timeout), self._safe_phrase_limit(phrase_time_limit))
            print("Vyom : Audio captured. Processing speech...", flush=True)
            result = self._recognize_wake(audio) if wake_mode else self._recognize_command(audio)
            if result.get("success"):
                print("You : " + str(result.get("text", "")), flush=True)
            else:
                self._log("Recognition status: " + str(result.get("status", "")))
            return result

        except Exception as error:
            if self._is_device_error(error):
                self._device_error_count += 1
                self._session_active = False
                self._log("Audio device error: " + str(error))
                return {
                    "success": False, "text": "", "language": "",
                    "status": "device_error", "message": str(error),
                }

            message = str(error).lower()
            if "waittimeout" in message or "timed out" in message or "timeout" in message:
                self._last_status = "silence"
                self._log("No speech detected.")
                return {
                    "success": False, "text": "", "language": "",
                    "status": "silence", "message": "No speech detected.",
                }

            self._last_status = "error"
            self._log("STT listen error: " + str(error))
            return {
                "success": False, "text": "", "language": "",
                "status": "error", "message": str(error),
            }

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
        self.start_session()
        try:
            while True:
                result = self.listen(timeout=5, phrase_time_limit=8, announce=True, wake_mode=False)
                print(result)
                if result.get("text", "").strip().lower() in {"exit", "quit", "stop"}:
                    break
        finally:
            self.stop_session()


if __name__ == "__main__":
    SpeechToText().test()

