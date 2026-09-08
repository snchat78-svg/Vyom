"""Vyom AI - Speech-to-Text layer.

The voice controller owns wake-word/session state. This module only:
    microphone -> audio -> speech text

Google recognition is bounded by SpeechRecognition's operation_timeout.
One captured utterance is sent to Google only once by default; this prevents
Hindi/English fallback requests from making the voice loop appear frozen.
"""

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

    def __init__(self, preferred_language="hi-IN", fallback_language="en-IN", debug=True):
        self.recognizer = None
        self.microphone = None
        self.available = False
        self.error_message = ""
        self.debug = bool(debug)
        self.preferred_language = preferred_language
        self.fallback_language = fallback_language
        self._session_active = False
        self._session_source = None
        self._last_text = ""
        self._last_language = ""
        self._last_status = ""
        self._device_error_count = 0
        self._recognition_error_count = 0
        self._sr_module = None
        self._initialize()

    def _log(self, message):
        if self.debug:
            try:
                print("[STT] " + str(message), flush=True)
            except Exception:
                pass

    def _configure_recognizer(self, sr):
        self.recognizer = sr.Recognizer()
        self.recognizer.pause_threshold = self.pause_threshold
        self.recognizer.non_speaking_duration = self.non_speaking_duration
        self.recognizer.phrase_threshold = self.phrase_threshold
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.energy_threshold = self.initial_energy_threshold
        self.recognizer.dynamic_energy_adjustment_damping = self.dynamic_energy_adjustment_damping
        self.recognizer.dynamic_energy_ratio = self.dynamic_energy_ratio
        self.recognizer.operation_timeout = self.google_request_timeout

    def _initialize(self):
        self._log("Initializing Speech-To-Text...")
        try:
            import speech_recognition as sr
            self._sr_module = sr
            self._log("speech_recognition import: OK")
            self._configure_recognizer(sr)
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
    def _text_error(error):
        return str(error or "").lower()

    def _is_device_error(self, error):
        msg = self._text_error(error)
        return any(x in msg for x in (
            "winerror 31", "device attached", "no default input device",
            "invalid input device", "input device", "permissionerror",
            "audio device", "paerror", "portaudio", "wasapi",
            "directsound", "mmdevice", "microphone"
        ))

    def _is_network_error(self, error):
        msg = self._text_error(error)
        return any(x in msg for x in (
            "requesterror", "connection", "network", "urlopen",
            "timed out", "timeout", "service unavailable",
            "remote end closed", "connection reset", "connection aborted",
            "connection refused", "name or service not known",
            "temporary failure"
        ))

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
        if not self.available:
            return False
        if self._session_active:
            return True
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
        self._close_microphone()
        self._session_active = False
        self._log("Microphone session stopped.")

    def recover_session(self):
        self._log("Recovery start.")
        self._reset_audio_device()
        if self.start_session():
            self._log("Microphone session restored.")
            return True
        self._log("Reinitializing Speech-To-Text...")
        self._initialize()
        return self.start_session() if self.available else False

    @staticmethod
    def _safe_number(value, default):
        try:
            value = float(value)
            return value if value > 0 else None
        except (TypeError, ValueError):
            return default

    def _recognize_google(self, audio, language, show_all=False):
        self.recognizer.operation_timeout = self.google_request_timeout
        return self.recognizer.recognize_google(audio, language=language, show_all=show_all)

    @staticmethod
    def _extract_google_text(result):
        if isinstance(result, str):
            return result.strip()
        if not isinstance(result, dict):
            return ""
        alternatives = result.get("alternative") or []
        if not alternatives:
            return ""
        return str(alternatives[0].get("transcript", "") or "").strip()

    def _recognize(self, audio, language):
        started = time.time()
        self._log("STT request started: " + str(language))
        try:
            text = self._recognize_google(audio, language, show_all=False)
            text = str(text or "").strip()
            self._log("STT request finished: %s in %.2fs" % (language, time.time() - started))
            return {"success": bool(text), "text": text, "language": language,
                    "status": "recognized" if text else "unrecognized"}
        except Exception as error:
            self._log("STT request ended with error: %s after %.2fs" % (str(error), time.time() - started))
            lower = self._text_error(error)
            if "unknownvalue" in lower or "could not understand" in lower or "unknown value" in lower:
                return {"success": False, "text": "", "language": language, "status": "unrecognized"}
            if self._is_device_error(error):
                self._device_error_count += 1
                self._reset_audio_device()
                return {"success": False, "text": "", "language": "", "status": "device_error", "message": str(error)}
            if self._is_network_error(error) or "timeout" in lower or "timed out" in lower:
                return {"success": False, "text": "", "language": language, "status": "network_error", "message": str(error)}
            return {"success": False, "text": "", "language": language, "status": "recognition_error", "message": str(error)}

    def _recognize_wake(self, audio):
        """Recognize wake speech once and inspect Google alternatives.

        The controller remains the single owner of wake-word policy. The
        alternatives are only used to improve recognition of short wake words.
        """
        started = time.time()
        language = self.preferred_language or self.fallback_language or "en-IN"
        self._log("WAKE STT request started: " + str(language))
        try:
            result = self._recognize_google(audio, language, show_all=True)
            text = self._extract_google_text(result)
            self._log("WAKE STT request finished in %.2fs" % (time.time() - started))
            if text:
                return {"success": True, "text": text, "language": language, "status": "recognized"}
            return {"success": False, "text": "", "language": language, "status": "unrecognized"}
        except Exception as error:
            self._log("WAKE STT error: " + str(error))
            lower = self._text_error(error)
            if self._is_device_error(error):
                self._reset_audio_device()
                return {"success": False, "text": "", "language": "", "status": "device_error", "message": str(error)}
            if "unknownvalue" in lower or "could not understand" in lower or "unknown value" in lower:
                return {"success": False, "text": "", "language": language, "status": "unrecognized"}
            return {"success": False, "text": "", "language": language, "status": "network_error" if self._is_network_error(error) or "timeout" in lower else "recognition_error", "message": str(error)}

    def listen(self, timeout=5, phrase_time_limit=8, announce=True, wake_mode=None):
        if not self.available:
            return {"success": False, "text": "", "language": "", "status": "unavailable", "message": self.error_message}
        source = self._session_source
        temporary = False
        if wake_mode is None:
            wake_mode = not bool(announce)
        try:
            if not self._session_active:
                source = self.microphone.__enter__()
                temporary = True
            print("Vyom : Listening for wake word..." if wake_mode else "Vyom : Listening...", flush=True)
            audio = self.recognizer.listen(source, timeout=self._safe_number(timeout, self.recognition_timeout),
                                           phrase_time_limit=self._safe_number(phrase_time_limit, 8))
            if audio is None:
                return {"success": False, "text": "", "language": "", "status": "no_audio"}
            print("Vyom : Audio captured. Processing speech...", flush=True)
            result = self._recognize_wake(audio) if wake_mode else self._recognize(audio, self.preferred_language or self.fallback_language)
            self._last_text = result.get("text", "")
            self._last_language = result.get("language", "")
            self._last_status = result.get("status", "")
            if result.get("success"):
                print("You : " + result.get("text", ""), flush=True)
            else:
                self._log("Recognition status: " + str(result.get("status", "")))
            return result
        except Exception as error:
            if self._is_device_error(error):
                self._device_error_count += 1
                self._reset_audio_device()
                return {"success": False, "text": "", "language": "", "status": "device_error", "message": str(error)}
            msg = str(error).lower()
            if "waittimeout" in msg or "timed out" in msg or "timeout" in msg:
                return {"success": False, "text": "", "language": "", "status": "silence", "message": "No speech detected."}
            self._log("STT listen error: " + str(error))
            return {"success": False, "text": "", "language": "", "status": "error", "message": str(error)}
        finally:
            if temporary and source is not None:
                try:
                    source.__exit__(None, None, None)
                except Exception:
                    pass

    def listen_once(self, timeout=5, phrase_time_limit=8, announce=True):
        return self.listen(timeout=timeout, phrase_time_limit=phrase_time_limit, announce=announce,
                           wake_mode=not bool(announce))

    def recognize(self, audio):
        return self._recognize(audio, self.preferred_language or self.fallback_language)

    def test(self):
        if not self.available:
            print("STT Status : NOT AVAILABLE")
            print("Reason : " + self.error_message)
            return
        print("STT Status : READY")
        if not self.start_session():
            return
        try:
            print(self.listen(timeout=5, phrase_time_limit=8, announce=True, wake_mode=False))
        finally:
            self.stop_session()


if __name__ == "__main__":
    SpeechToText().test()
