"""Vyom AI persistent voice session controller.

Architecture:
    SLEEP -> wake word -> ACTIVE SESSION -> listen -> execute -> speak
                                              -> listen again -> ...

There is no push-to-talk cycle. The microphone session stays open after
startup and remains active until an explicit exit command.
"""

import difflib
import re
import time

from .speech_to_text import SpeechToText
from .text_to_speech import TextToSpeech
from ai_core.conversation_manager import ConversationManager


class VoiceController:
    def __init__(self, stt=None, tts=None, conversation_manager=None):
        self.speech_to_text = stt or SpeechToText(preferred_language="hi-IN", fallback_language="en-IN", debug=True)
        self.text_to_speech = tts or TextToSpeech(rate=165, volume=1.0, debug=True)
        self.conversation_manager = conversation_manager or ConversationManager()
        self.running = False
        self.state = "idle"
        self.activated = False
        self.continuous_conversation = True
        self.last_listen_status = ""
        self.wake_words = ("vyom", "व्योम", "व्योम जी", "hey vyom", "हे व्योम")
        self.wake_aliases = ("vyom", "व्योम", "व्योम जी", "hey vyom", "hey व्योम", "हे व्योम",
                             "वियम", "वियॉम", "व्योमजी", "व्योम जि", "biom", "viyom", "vyam")

    def _log(self, message):
        try:
            print("[VOICE] " + str(message), flush=True)
        except Exception:
            pass

    def _safe_print(self, message):
        try:
            print(message, flush=True)
        except Exception:
            pass

    def is_available(self):
        return bool(self.speech_to_text.is_available())

    def is_tts_available(self):
        return bool(self.text_to_speech.is_available())

    def speak(self, text):
        self.state = "speaking"
        try:
            result = self.text_to_speech.speak(text)
            return result if isinstance(result, dict) else {"success": bool(result)}
        except Exception as error:
            self._log("TTS ERROR: " + str(error))
            return {"success": False, "message": str(error)}

    @staticmethod
    def _normalize_wake_text(text):
        value = str(text or "").lower().strip()
        value = re.sub(r"[^\w\s\u0900-\u097F]", " ", value, flags=re.UNICODE)
        return re.sub(r"\s+", " ", value).strip()

    def _compact(self, text):
        return re.sub(r"\s+", "", self._normalize_wake_text(text))

    def _wake_candidates(self):
        values = []
        for item in self.wake_words + self.wake_aliases:
            n = self._normalize_wake_text(item)
            c = self._compact(item)
            if n and n not in values:
                values.append(n)
            if c and c not in values:
                values.append(c)
        return values

    def _is_wake_word(self, text):
        normalized = self._normalize_wake_text(text)
        compact = self._compact(text)
        if not normalized:
            return False
        candidates = self._wake_candidates()
        if normalized in candidates or compact in candidates:
            return True
        for candidate in candidates:
            if len(candidate) >= 3 and (candidate in normalized or candidate in compact):
                return True
        if len(normalized) <= 15:
            for candidate in candidates:
                if len(candidate) <= 15 and difflib.SequenceMatcher(None, normalized, candidate).ratio() >= 0.78:
                    return True
        return False

    def _find_wake_word(self, text):
        normalized = self._normalize_wake_text(text)
        if not normalized:
            return None
        for candidate in self.wake_words + self.wake_aliases:
            n = self._normalize_wake_text(candidate)
            if n and n in normalized:
                return n
        # Fuzzy detection is deliberately limited to short recognized text.
        if len(normalized) <= 15:
            best = None
            score = 0.0
            for candidate in self._wake_candidates():
                if len(candidate) > 15:
                    continue
                ratio = difflib.SequenceMatcher(None, normalized, candidate).ratio()
                if ratio > score:
                    score, best = ratio, candidate
            if score >= 0.78:
                return best
        return None

    def _remove_wake_word(self, text):
        value = str(text or "").strip()
        for candidate in sorted(self.wake_words + self.wake_aliases, key=len, reverse=True):
            pattern = re.compile(r"\b" + re.escape(candidate) + r"\b", re.IGNORECASE)
            new = pattern.sub(" ", value, count=1)
            if new != value:
                return re.sub(r"\s+", " ", new).strip()
        # Hindi/Unicode word boundaries can be inconsistent; exact substring fallback.
        normalized = self._normalize_wake_text(value)
        for candidate in sorted(self.wake_words + self.wake_aliases, key=len, reverse=True):
            n = self._normalize_wake_text(candidate)
            if n and n in normalized:
                return re.sub(r"\s+", " ", normalized.replace(n, " ", 1)).strip()
        return value

    def _activate(self):
        self.activated = True
        self.state = "active"
        self._log("WAKE WORD DETECTED -> ACTIVE SESSION")

    def process_text(self, text):
        text = str(text or "").strip()
        if not text:
            return {"success": False, "text": "", "message": "No command received.", "result": None}
        self.state = "processing"
        try:
            result = self.conversation_manager.process_voice(text)
            message = result.get("response", result.get("message", "")) if isinstance(result, dict) else str(result)
            return {"success": bool(result.get("success", False)) if isinstance(result, dict) else True,
                    "text": text, "message": str(message or ""), "result": result}
        except Exception as error:
            return {"success": False, "text": text, "message": "Command execution failed: " + str(error), "result": None}

    def listen_once(self, announce=False, timeout=5, phrase_time_limit=8, wake_mode=None):
        try:
            result = self.speech_to_text.listen(timeout=timeout, phrase_time_limit=phrase_time_limit,
                                               announce=announce, wake_mode=wake_mode)
        except Exception as error:
            self._log("STT listen_once error: " + str(error))
            return {"success": False, "status": "error", "text": "", "message": str(error)}
        if not isinstance(result, dict):
            result = {"success": bool(result), "status": "unknown", "text": ""}
        self.last_listen_status = str(result.get("status", ""))
        return result

    def _recover_microphone(self):
        self._log("AUDIO ERROR -> RECOVERY")
        recover = getattr(self.speech_to_text, "recover_session", None)
        if callable(recover):
            restored = bool(recover())
        else:
            stop = getattr(self.speech_to_text, "stop_session", None)
            start = getattr(self.speech_to_text, "start_session", None)
            if callable(stop):
                stop()
            restored = bool(start()) if callable(start) else False
        if restored:
            self._log("MICROPHONE SESSION RESTORED")
        return restored

    def _wait_for_activation(self):
        self.state = "waiting_for_wake"
        self._log("WAITING_FOR_WAKE")
        result = self.listen_once(announce=False, timeout=2.5, phrase_time_limit=4, wake_mode=True)
        if not result.get("success"):
            if result.get("status") == "device_error":
                self._recover_microphone()
            return {"activated": False, "command": "", "wake_word": None, "text": ""}
        text = str(result.get("text", "")).strip()
        if not text:
            return {"activated": False, "command": "", "wake_word": None, "text": ""}
        self._safe_print("Wake speech -> " + text)
        wake_word = self._find_wake_word(text)
        if not wake_word:
            self._log("Recognized speech but no wake word.")
            return {"activated": False, "command": "", "wake_word": None, "text": text}
        self._activate()
        command = self._remove_wake_word(text)
        self._safe_print("Wake word detected -> " + str(wake_word))
        if command:
            self._safe_print("Command after wake -> " + command)
        return {"activated": True, "command": command, "wake_word": wake_word, "text": text}

    def _listen_active_command(self):
        self.state = "listening"
        self._safe_print("Vyom : Listening for your command...")
        result = self.listen_once(announce=False, timeout=5, phrase_time_limit=8, wake_mode=False)
        if not result.get("success"):
            if result.get("status") == "device_error":
                self._recover_microphone()
            return ""
        command = str(result.get("text", "")).strip()
        if command:
            self._log("ACTIVE COMMAND RECEIVED: " + command)
        return command

    def _is_exit_command(self, text):
        value = self._normalize_wake_text(text)
        return value in {"exit", "quit", "stop listening", "shutdown voice", "bye", "goodbye",
                         "बंद हो जाओ", "बंद करो", "रुक जाओ", "रुक जाओ व्योम", "बाय", "अलविदा"}

    def _speak_response(self, response):
        response = str(response or "").strip()
        if not response:
            self.state = "listening"
            return
        self._safe_print("Vyom : " + response)
        self.speak(response)
        if self.running:
            time.sleep(0.25)
            self.state = "listening"

    def _speak_startup_response(self):
        return self.speak("नमस्ते, मैं व्योम हूँ। मुझे जगाने के लिए व्योम कहिए।")

    def _speak_activation_response(self):
        self._speak_response("हाँ, बताइए।")

    def _execute_voice_command(self, command):
        command = str(command or "").strip()
        if not command:
            return {"success": False, "text": "", "message": "", "result": None}
        if self._is_exit_command(command):
            self._speak_response("ठीक है। मैं सुनना बंद कर रहा हूँ।")
            self.activated = False
            self.running = False
            self.state = "idle"
            self._stop_audio_sessions()
            return {"success": True, "text": command, "message": "Voice session stopped.", "result": None}
        self._safe_print("Processing -> " + command)
        result = self.process_text(command)
        message = str(result.get("message", "") or "").strip()
        if message:
            self._speak_response(message)
        return result

    def _stop_audio_sessions(self):
        stop_stt = getattr(self.speech_to_text, "stop_session", None)
        if callable(stop_stt):
            try:
                stop_stt()
            except Exception:
                pass
        stop_tts = getattr(self.text_to_speech, "stop", None)
        if callable(stop_tts):
            try:
                stop_tts()
            except Exception:
                pass

    def run(self):
        self._safe_print("=" * 60)
        self._safe_print("Vyom AI - Voice Engine v2.0")
        self._safe_print("=" * 60)
        if not self.speech_to_text.is_available():
            self._safe_print("Vyom : Speech-To-Text is not available.")
            self._safe_print("Reason : " + str(self.speech_to_text.error_message))
            return False
        if not self.text_to_speech.is_available():
            self._safe_print("Vyom : Text-To-Speech is not available; voice output is disabled.")
        self.running = True
        self.activated = False
        self.state = "idle"
        try:
            if self.text_to_speech.is_available():
                self._speak_startup_response()
            if not self.speech_to_text.start_session():
                self._safe_print("Vyom : Microphone could not be started.")
                return False
            self._safe_print("Vyom : Voice engine is ready.")
            self._safe_print("Vyom : Say 'Vyom' to activate.")
            while self.running:
                if not self.activated:
                    activation = self._wait_for_activation()
                    if not activation.get("activated"):
                        continue
                    command = activation.get("command", "")
                    if command:
                        self._execute_voice_command(command)
                        if self.running:
                            self.activated = True
                        continue
                    self.activated = True
                    self.state = "active"
                    self._speak_activation_response()
                command = self._listen_active_command()
                if not command:
                    continue
                self._execute_voice_command(command)
                if self.running and self.continuous_conversation:
                    self.activated = True
                    self.state = "listening"
                    self._log("READY FOR NEXT COMMAND")
                elif self.running:
                    self.activated = False
                    self.state = "waiting_for_wake"
        except KeyboardInterrupt:
            self._log("KeyboardInterrupt received.")
        except Exception as error:
            self._log("VOICE ENGINE ERROR: " + str(error))
        finally:
            self.running = False
            self.activated = False
            self.state = "idle"
            self._stop_audio_sessions()
        return True

    def stop(self):
        self.running = False
        self.activated = False
        self.state = "idle"
        self._stop_audio_sessions()
