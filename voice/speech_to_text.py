"""Vyom AI - reliable speech-to-text boundary.

Design:
    logical voice session -> capture one utterance -> recognize -> preserve
    raw transcript -> normalize command to Roman text.

The existing microphone/session/recovery behavior is preserved.
"""

import difflib
import re
import sys
import time

from .romanizer import normalize_voice_text


class SpeechToText:
    recognition_timeout = 4
    google_request_timeout = 4
    initial_energy_threshold = 250
    dynamic_energy_adjustment_damping = 0.15
    dynamic_energy_ratio = 1.5
    pause_threshold = 0.80
    non_speaking_duration = 0.45
    phrase_threshold = 0.20
    recovery_delay = 0.35
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
        self._last_text = ""
        self._last_raw_text = ""
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
            value = str(message)
            safe_value = value.encode("unicode_escape", errors="backslashreplace").decode("ascii")
            print("[STT] " + safe_value, flush=True)
        except Exception:
            pass

    @staticmethod
    def _safe_print(message):
        try:
            text = str(message)
            stream = getattr(sys, "stdout", None)
            if stream is None:
                return
            encoding = getattr(stream, "encoding", None) or "utf-8"
            try:
                text.encode(encoding)
            except (UnicodeEncodeError, LookupError):
                text = text.encode(encoding, errors="replace").decode(encoding, errors="replace")
            stream.write(text + "\n")
            stream.flush()
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
            "connection refused", "name or service not known", "temporary failure",
        ))

    def _is_unknown_speech(self, error):
        sr = self._sr_module
        unknown_type = getattr(sr, "UnknownValueError", None) if sr else None
        if unknown_type is not None:
            try:
                if isinstance(error, unknown_type):
                    return True
            except Exception:
                pass
        text = str(error or "").lower()
        return (
            "unknownvalue" in text or "unknown value" in text
            or "could not understand" in text or "couldn\'t understand" in text
        )

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

    def _recognize_google(self, audio, language, show_all=True):
        if self.recognizer is None:
            raise RuntimeError("Speech recognizer is not initialized.")
        self.recognizer.operation_timeout = self.google_request_timeout
        return self.recognizer.recognize_google(audio, language=language, show_all=show_all)

    @staticmethod
    def _extract_transcripts(payload):
        if isinstance(payload, str):
            text = payload.strip()
            return [text] if text else []
        if not isinstance(payload, dict):
            return []
        texts = []
        for item in payload.get("alternative") or []:
            if isinstance(item, dict):
                text = str(item.get("transcript") or "").strip()
                if text and text not in texts:
                    texts.append(text)
        return texts

    def _recognize_one(self, audio, language, label="STT", show_all=False):
        started = time.time()
        self._log("%s request started: %s" % (label, language))
        try:
            payload = self._recognize_google(audio, language, show_all=show_all)
            if isinstance(payload, dict):
                transcripts = self._extract_transcripts(payload)
            elif isinstance(payload, str):
                text_value = payload.strip()
                transcripts = [text_value] if text_value else []
            else:
                transcripts = []
                self._log("%s returned unsupported payload type: %s" % (label, type(payload).__name__))

            raw_text = transcripts[0] if transcripts else ""
            elapsed = time.time() - started
            self._log("%s request finished: %s in %.2fs" % (label, language, elapsed))
            self._log("%s raw transcript received: %s" % (label, raw_text if raw_text else "<empty>"))
            text = normalize_voice_text(raw_text)
            self._log("%s Roman transcript: %s" % (label, text if text else "<empty>"))

            return {
                "success": bool(text),
                "text": text,
                "raw_text": raw_text,
                "alternatives": [normalize_voice_text(item) for item in transcripts],
                "raw_alternatives": transcripts,
                "language": language,
                "status": "recognized" if text else "unrecognized",
            }
        except Exception as error:
            elapsed = time.time() - started
            self._recognition_error_count += 1
            message = str(error) or type(error).__name__
            self._log("%s request error: %s after %.2fs" % (label, message, elapsed))
            if self._is_device_error(error):
                self._device_error_count += 1
                return {"success": False, "text": "", "raw_text": "", "language": "", "status": "device_error", "message": message}
            if self._is_unknown_speech(error):
                return {"success": False, "text": "", "raw_text": "", "language": language, "status": "unrecognized", "message": message}
            if self._is_network_error(error):
                return {"success": False, "text": "", "raw_text": "", "language": language, "status": "network_error", "message": message}
            return {"success": False, "text": "", "raw_text": "", "language": language, "status": "recognition_error", "message": message}

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
        self._log("WAKE recognition cycle START")
        first = self._recognize_one(audio, "en-IN", label="WAKE STT", show_all=True)
        if first.get("status") == "device_error":
            self._last_status = "device_error"
            return first

        candidates = list(first.get("raw_alternatives") or [])
        if first.get("raw_text") and first.get("raw_text") not in candidates:
            candidates.insert(0, first.get("raw_text"))
        for raw_text in candidates:
            matched, alias = self._wake_detected(raw_text)
            if matched:
                text = normalize_voice_text(raw_text)
                self._last_raw_text = raw_text
                self._last_text = text
                self._last_language = "en-IN"
                self._last_status = "wake_detected"
                return {
                    "success": True, "text": text, "raw_text": raw_text,
                    "language": "en-IN", "status": "wake_detected",
                    "wake_word": normalize_voice_text(alias),
                }

        if first.get("status") in {"network_error", "recognition_error", "unrecognized"}:
            second = self._recognize_one(audio, "hi-IN", label="WAKE STT", show_all=True)
            if second.get("status") == "device_error":
                return second
            candidates = list(second.get("raw_alternatives") or [])
            if second.get("raw_text") and second.get("raw_text") not in candidates:
                candidates.insert(0, second.get("raw_text"))
            for raw_text in candidates:
                matched, alias = self._wake_detected(raw_text)
                if matched:
                    text = normalize_voice_text(raw_text)
                    self._last_raw_text = raw_text
                    self._last_text = text
                    self._last_language = "hi-IN"
                    self._last_status = "wake_detected"
                    return {
                        "success": True, "text": text, "raw_text": raw_text,
                        "language": "hi-IN", "status": "wake_detected",
                        "wake_word": normalize_voice_text(alias),
                    }

        raw_text = str(first.get("raw_text") or first.get("text") or "").strip()
        text = normalize_voice_text(raw_text)
        self._last_raw_text = raw_text
        self._last_text = text
        self._last_language = "en-IN" if text else ""
        self._last_status = "wake_not_detected" if text else "unrecognized"
        return {
            "success": False, "text": text, "raw_text": raw_text,
            "language": self._last_language, "status": self._last_status,
            "message": str(first.get("message", "") or ""),
        }

    def _recognize_command(self, audio):
        self._log("COMMAND recognition cycle START")
        first = self._recognize_one(audio, self.preferred_language, label="STT", show_all=False)
        if first.get("status") == "device_error":
            return first
        if first.get("success") or first.get("text"):
            raw_text = str(first.get("raw_text") or "").strip()
            text = normalize_voice_text(raw_text)
            self._last_raw_text = raw_text
            self._last_text = text
            self._last_language = self.preferred_language
            self._last_status = "recognized"
            return {
                "success": True, "text": text, "raw_text": raw_text,
                "alternatives": list(first.get("alternatives") or []),
                "raw_alternatives": list(first.get("raw_alternatives") or []),
                "language": self.preferred_language, "status": "recognized",
            }

        second = self._recognize_one(audio, self.fallback_language, label="STT", show_all=False)
        if second.get("status") == "device_error":
            return second
        if second.get("success") or second.get("text"):
            raw_text = str(second.get("raw_text") or "").strip()
            text = normalize_voice_text(raw_text)
            self._last_raw_text = raw_text
            self._last_text = text
            self._last_language = self.fallback_language
            self._last_status = "recognized"
            return {
                "success": True, "text": text, "raw_text": raw_text,
                "alternatives": list(second.get("alternatives") or []),
                "raw_alternatives": list(second.get("raw_alternatives") or []),
                "language": self.fallback_language, "status": "recognized",
            }

        self._last_status = "unrecognized"
        return {
            "success": False, "text": "", "raw_text": "", "language": "",
            "status": "unrecognized",
            "message": str(second.get("message") or first.get("message") or ""),
        }

    def _capture(self, timeout, phrase_time_limit):
        if self.microphone is None or self.recognizer is None:
            raise RuntimeError("Microphone or recognizer is not initialized.")
        self._log("Opening microphone for one utterance...")
        with self.microphone as source:
            self._log("Waiting for speech...")
            audio = self.recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
        self._log("Audio capture COMPLETE; microphone released.")
        return audio

    def listen(self, timeout=5, phrase_time_limit=None, announce=True, wake_mode=None):
        if not self.available:
            return {"success": False, "text": "", "raw_text": "", "language": "", "status": "unavailable", "message": self.error_message}
        if wake_mode is None:
            wake_mode = not bool(announce)
        try:
            self._log("CAPTURE START: mode=%s timeout=%s phrase_limit=%s session=%s" % (
                "WAKE" if wake_mode else "COMMAND", timeout, phrase_time_limit, self._session_active
            ))
            audio = self._capture(self._safe_timeout(timeout), self._safe_phrase_limit(phrase_time_limit))
            self._safe_print("Vyom : Audio captured. Processing speech...")
            result = self._recognize_wake(audio) if wake_mode else self._recognize_command(audio)
            if not result.get("success"):
                self._log("Recognition status: " + str(result.get("status", "")))
            self._log("LISTEN RESULT RETURN: status=%s success=%s text_length=%d" % (
                str(result.get("status", "")), bool(result.get("success", False)),
                len(str(result.get("text", "") or "")),
            ))
            return result
        except Exception as error:
            if self._is_device_error(error):
                self._device_error_count += 1
                self._session_active = False
                return {"success": False, "text": "", "raw_text": "", "language": "", "status": "device_error", "message": str(error)}
            message = str(error).lower()
            if "waittimeout" in message or "timed out" in message or "timeout" in message:
                self._last_status = "silence"
                return {"success": False, "text": "", "raw_text": "", "language": "", "status": "silence", "message": "No speech detected."}
            self._last_status = "error"
            return {"success": False, "text": "", "raw_text": "", "language": "", "status": "error", "message": str(error)}

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

    def listen_once(self, timeout=5, phrase_time_limit=None, announce=True):
        return self.listen(timeout=timeout, phrase_time_limit=phrase_time_limit, announce=announce, wake_mode=not bool(announce))

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
                result = self.listen(timeout=5, phrase_time_limit=None, announce=True, wake_mode=False)
                print(result)
                if result.get("text", "").strip().lower() in {"exit", "quit", "stop"}:
                    break
        finally:
            self.stop_session()


if __name__ == "__main__":
    SpeechToText().test()
