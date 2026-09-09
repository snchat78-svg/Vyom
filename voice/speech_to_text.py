# voice/speech_to_text.py

import re, time
import speech_recognition as sr

class SpeechToText:
    """
    Handles microphone capture and Google STT with Hindi/English fallback.
    Uses per-utterance audio capture (no persistent stream).
    """
    def __init__(self, preferred_language="hi-IN", fallback_language="en-IN", debug=True):
        self.recognizer = None
        self.preferred_language = preferred_language
        self.fallback_language = fallback_language
        self.available = False
        self.error_message = ""
        self.debug = debug
        self._initialize()

    def _log(self, msg):
        if self.debug:
            print("[STT] " + str(msg), flush=True)

    def _initialize(self):
        self._log("Initializing Speech-To-Text...")
        try:
            self.recognizer = sr.Recognizer()
            # Configure recognizer (thresholds etc.)
            self.recognizer.pause_threshold = 0.65
            self.recognizer.non_speaking_duration = 0.35
            self.recognizer.phrase_threshold = 0.20
            self.recognizer.dynamic_energy_threshold = True
            self.recognizer.energy_threshold = 250
            self.recognizer.operation_timeout = 10  # Google API timeout
            self.available = True
            self.error_message = ""
            self._log("Speech-To-Text READY.")
        except Exception as e:
            self.available = False
            self.error_message = str(e)
            self._log("STT initialization failed: " + str(e))

    def is_available(self):
        return self.available

    def _safe_timeout(self, timeout):
        try:
            value = float(timeout)
            return None if value <= 0 else value
        except:
            return None

    def _safe_phrase_limit(self, phrase_time_limit):
        try:
            value = float(phrase_time_limit)
            return None if value <= 0 else value
        except:
            return None

    def _recognize_google(self, audio, language):
        # Use recognizer.operation_timeout to bound network wait
        self.recognizer.operation_timeout = 8
        return self.recognizer.recognize_google(audio, language=language)

    def _recognize_with_fallback(self, audio, wake_mode=False):
        """
        Try preferred_language then fallback_language.
        For wake_mode=True, only return success if wake word detected.
        """
        languages = []
        if self.preferred_language:
            languages.append(self.preferred_language)
        if self.fallback_language and self.fallback_language not in languages:
            languages.append(self.fallback_language)
        if not languages:
            return {"success": False, "text": "", "language": "", "status": "no_language"}

        results = []
        for lang in languages:
            self._log(f"STT request started: {lang}")
            start_time = time.time()
            try:
                text = self._recognize_google(audio, lang)
                elapsed = time.time() - start_time
                text = text.strip()
                self._log(f"STT request finished: {lang} in {elapsed:.2f}s")
                if not text:
                    continue
                self._log(f"STT result [{lang}]: {text}")
                results.append((lang, text))

                if not wake_mode:
                    return {"success": True, "text": text, "language": lang, "status": "recognized"}
                else:
                    # In wake mode, we'll check wake word elsewhere
                    return {"success": True, "text": text, "language": lang, "status": "wake_detected"}

            except Exception as error:
                msg = str(error).lower()
                if "unknownvalue" in msg or "could not understand" in msg:
                    continue
                if "timeout" in msg or "timed out" in msg:
                    self._log(f"STT recognition timeout [{lang}]")
                    continue
                if "requesterror" in msg or "connection" in msg or "network" in msg:
                    self._log(f"STT network error [{lang}]: {error}")
                    continue
                self._log(f"Recognition error [{lang}]: {error}")
                continue

        # If we're here, nothing recognized
        return {"success": False, "text": "", "language": "", "status": "unrecognized"}

    def listen(self, timeout=5, phrase_time_limit=8, announce=True, wake_mode=None):
        """
        Listen once (one utterance). In wake_mode, we just attempt to detect the wake word.
        """
        if not self.available:
            return {"success": False, "status": "unavailable", "text": "", "message": self.error_message}
        if wake_mode is None:
            wake_mode = not bool(announce)

        self._log("listen() called.")
        try:
            # Capture one utterance
            source = None
            try:
                source = sr.Microphone()  # create new microphone source
            except Exception as e:
                self._log(f"Microphone open failed: {e}")
                return {"success": False, "status": "device_error", "text": "", "message": str(e)}

            with source as mic:
                self._log(f"CAPTURE START: mode={'WAKE' if wake_mode else 'COMMAND'} timeout={timeout} phrase_limit={phrase_time_limit}")
                if wake_mode:
                    print("Vyom : Listening for wake word...", flush=True)
                else:
                    print("Vyom : Listening...", flush=True)
                audio = self.recognizer.listen(
                    mic,
                    timeout=self._safe_timeout(timeout),
                    phrase_time_limit=self._safe_phrase_limit(phrase_time_limit)
                )
            if audio is None:
                return {"success": False, "text": "", "language": "", "status": "no_audio", "message": "No audio captured."}

            print("Vyom : Audio captured. Processing speech...", flush=True)
            self._log("Audio capture COMPLETE.")

            # Recognize
            result = self._recognize_with_fallback(audio, wake_mode=wake_mode)
            self._log(f"Recognition status: {result.get('status','')}")
            if result.get("success"):
                print("You : " + result.get("text",""), flush=True)
            return result

        except Exception as e:
            # Audio device errors
            msg = str(e).lower()
            if any(err in msg for err in ("device", "permission", "paerror", "portaudio", "no default")):
                self._log("Audio capture device error: " + str(e))
                return {"success": False, "status": "device_error", "text": "", "message": str(e)}
            self._log("STT listen error: " + str(e))
            return {"success": False, "status": "error", "text": "", "message": str(e)}
