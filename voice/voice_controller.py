"""Vyom AI - persistent voice conversation controller.

The session is persistent, but the physical microphone is opened only during
an individual capture. This avoids Windows audio contention with SAPI/pyttsx3
while preserving fully automatic, push-to-talk-free conversation.
"""

import difflib
import re
import time

from .speech_to_text import SpeechToText
from .text_to_speech import TextToSpeech
from ai_core.conversation_manager import ConversationManager


class VoiceController:
    def __init__(self, stt=None, tts=None, conversation_manager=None):
        self.speech_to_text = stt or SpeechToText(
            preferred_language="hi-IN", fallback_language="en-IN", debug=True
        )
        self.text_to_speech = tts or TextToSpeech(rate=165, volume=1.0, debug=True)
        self.conversation_manager = conversation_manager or ConversationManager()

        self.running = False
        self.state = "idle"
        self.activated = False
        self.continuous_conversation = True
        self.last_listen_status = ""

        self.wake_words = (
            "hey vyom", "हे व्योम", "vyom ji", "व्योम जी", "vyom", "व्योम",
            "viyom", "वियोम", "वियम", "वियॉम", "vyam", "biom",
        )

    @staticmethod
    def _safe_print(message):
        try:
            print(message, flush=True)
        except Exception:
            pass

    def _log(self, message):
        try:
            print("[VOICE] " + str(message), flush=True)
        except Exception:
            pass

    def is_available(self):
        try:
            return bool(self.speech_to_text.is_available())
        except Exception:
            return False

    def is_tts_available(self):
        try:
            return bool(self.text_to_speech.is_available())
        except Exception:
            return False

    def speak(self, text):
        self.state = "speaking"
        self._log("STATE -> SPEAKING")
        self._log("TTS response started.")
        try:
            result = self.text_to_speech.speak(text)
            if not isinstance(result, dict):
                result = {"success": bool(result)}
            self._log("TTS response completed: %s" % bool(result.get("success", False)))
            return result
        except Exception as error:
            self._log("TTS ERROR: " + str(error))
            return {"success": False, "message": str(error)}

    @staticmethod
    def _normalize(text):
        value = str(text or "").lower().strip()
        value = re.sub(r"[^\w\s\u0900-\u097F]", " ", value, flags=re.UNICODE)
        return re.sub(r"\s+", " ", value).strip()

    def _find_wake_word(self, text):
        normalized = self._normalize(text)
        if not normalized:
            return None

        for wake_word in sorted(self.wake_words, key=len, reverse=True):
            candidate = self._normalize(wake_word)
            if candidate and candidate in normalized:
                return candidate

        compact = normalized.replace(" ", "")
        if len(normalized) <= 24:
            best = None
            score = 0.0
            for wake_word in self.wake_words:
                candidate = self._normalize(wake_word).replace(" ", "")
                if not candidate:
                    continue
                ratio = difflib.SequenceMatcher(None, compact, candidate).ratio()
                if ratio > score:
                    score = ratio
                    best = self._normalize(wake_word)
            if score >= 0.72:
                return best
        return None

    def _remove_wake_word(self, text):
        original = str(text or "").strip()
        if not original:
            return ""

        for wake_word in sorted(self.wake_words, key=len, reverse=True):
            pattern = re.compile(re.escape(wake_word), re.IGNORECASE)
            new_value = pattern.sub(" ", original, count=1)
            if new_value != original:
                return re.sub(r"\s+", " ", new_value).strip()

        normalized = self._normalize(original)
        for wake_word in sorted(self.wake_words, key=len, reverse=True):
            candidate = self._normalize(wake_word)
            if candidate and candidate in normalized:
                return re.sub(r"\s+", " ", normalized.replace(candidate, " ", 1)).strip()
        return original

    def _activate(self):
        self.activated = True
        self.state = "active"
        self._log("WAKE WORD DETECTED")
        self._log("STATE -> ACTIVE SESSION")

    def process_text(self, text):
        command = str(text or "").strip()
        if not command:
            return {"success": False, "text": "", "message": "No command received.", "result": None}

        self.state = "processing"
        self._log("STATE -> PROCESSING")
        try:
            self.state = "executing"
            self._log("STATE -> EXECUTING")
            result = self.conversation_manager.process_voice(command)
            if isinstance(result, dict):
                success = bool(result.get("success", False))
                message = result.get("response", result.get("message", ""))
            else:
                success = True
                message = str(result)
            self._log("EXECUTION COMPLETE")
            return {"success": success, "text": command, "message": str(message or ""), "result": result}
        except Exception as error:
            self._log("Execution error: " + str(error))
            return {"success": False, "text": command, "message": "Command execution failed: " + str(error), "result": None}

    def listen_once(self, announce=False, timeout=5, phrase_time_limit=8, wake_mode=None):
        try:
            result = self.speech_to_text.listen(
                timeout=timeout,
                phrase_time_limit=phrase_time_limit,
                announce=announce,
                wake_mode=wake_mode,
            )
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
        try:
            restored = bool(recover()) if callable(recover) else False
        except Exception as error:
            self._log("Recovery failed: " + str(error))
            restored = False
        if restored:
            self._log("MICROPHONE CAPTURE RESTORED")
            self._log("RESUMING LISTENING")
        return restored

    def _wait_for_activation(self):
        self.state = "waiting_for_wake"
        self._log("WAITING_FOR_WAKE")
        result = self.listen_once(
            announce=False, timeout=2.5, phrase_time_limit=4, wake_mode=True
        )
        status = str(result.get("status", ""))
        if status == "device_error":
            self._recover_microphone()
            return {"activated": False, "command": "", "wake_word": None, "text": ""}

        text = str(result.get("text", "") or "").strip()
        wake_word = str(result.get("wake_word", "") or "").strip() or self._find_wake_word(text)
        wake_ok = bool(result.get("success")) and (status == "wake_detected" or bool(wake_word))

        if not wake_ok:
            self._log("Wake listen status: " + status)
            return {"activated": False, "command": "", "wake_word": None, "text": text}

        self._safe_print("Wake speech -> " + text)
        self._safe_print("Wake word detected -> " + (wake_word or "Vyom"))
        self._activate()

        command = self._remove_wake_word(text)
        if command:
            self._safe_print("Command after wake -> " + command)
        return {"activated": True, "command": command, "wake_word": wake_word or "Vyom", "text": text}

    def _listen_active_command(self):
        self.state = "listening"
        self._log("STATE -> LISTENING")
        self._safe_print("Vyom : Listening for your command...")
        result = self.listen_once(
            announce=False, timeout=5, phrase_time_limit=10, wake_mode=False
        )
        status = str(result.get("status", ""))
        self.last_listen_status = status
        if status == "device_error":
            self._recover_microphone()
            return ""
        if not result.get("success"):
            self._log("Active listen status: " + status)
            return ""
        command = str(result.get("text", "") or "").strip()
        if command:
            self._safe_print("Command detected -> " + command)
            self._log("ACTIVE COMMAND RECEIVED")
        return command

    def _is_exit_command(self, text):
        value = self._normalize(text)
        return value in {
            "exit", "quit", "stop listening", "shutdown voice", "bye", "goodbye", "stop",
            "बंद हो जाओ", "बंद करो", "रुक जाओ", "रुक जाओ व्योम", "सुनना बंद करो", "बाय", "अलविदा",
        }

    def _pause_microphone_for_speech(self):
        # v4 STT has no persistent physical stream. This method exists for
        # compatibility and makes the transition explicit in the logs.
        self._log("MICROPHONE PHYSICAL STREAM = RELEASED FOR TTS")

    def _speak_response(self, response):
        message = str(response or "").strip()
        if not message:
            self.state = "listening"
            return
        self._pause_microphone_for_speech()
        self._safe_print("Vyom : " + message)
        self.speak(message)
        if self.running:
            time.sleep(0.30)
            self.state = "listening"
            self._log("READY TO LISTEN AGAIN")

    def _speak_startup_response(self):
        return self.speak("नमस्ते, मैं व्योम हूँ। मुझे जगाने के लिए व्योम कहिए।")

    def _speak_activation_response(self):
        self._log("ACTIVATION TTS BEGIN")
        result = self._speak_response("हाँ, बताइए।")
        self._log("ACTIVATION TTS END")
        return result

    def _execute_voice_command(self, command):
        command = str(command or "").strip()
        if not command:
            return {"success": False, "text": "", "message": "", "result": None}

        if self._is_exit_command(command):
            self._log("Exit command detected.")
            self._speak_response("ठीक है। मैं सुनना बंद कर रहा हूँ।")
            self.activated = False
            self.running = False
            self.state = "idle"
            self._stop_audio_sessions()
            return {"success": True, "text": command, "message": "Voice session stopped.", "result": None}

        self._safe_print("Processing -> " + command)
        result = self.process_text(command)
        response = str(result.get("message", "") or "").strip()
        if response:
            self._speak_response(response)
        else:
            self._safe_print("Vyom : Command completed.")
        return result

    def _stop_audio_sessions(self):
        stop_stt = getattr(self.speech_to_text, "stop_session", None)
        if callable(stop_stt):
            try:
                stop_stt()
            except Exception as error:
                self._log("STT cleanup error: " + str(error))
        stop_tts = getattr(self.text_to_speech, "stop", None)
        if callable(stop_tts):
            try:
                stop_tts()
            except Exception as error:
                self._log("TTS cleanup error: " + str(error))

    def run(self):
        self._safe_print("=" * 60)
        self._safe_print("Vyom AI - Voice Engine v4.0")
        self._safe_print("=" * 60)
        self._log("VOICE ENGINE STARTING...")

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
                self._log("STARTUP TTS BEGIN")
                self._speak_startup_response()
                self._log("STARTUP TTS END")

            self._log("Starting logical voice session AFTER startup TTS...")
            if not self.speech_to_text.start_session():
                self._safe_print("Vyom : Microphone could not be initialized.")
                return False

            self._safe_print("")
            self._safe_print("Vyom : Voice engine is ready.")
            self._safe_print("Vyom : Say 'Vyom' to activate.")
            self._safe_print("")

            while self.running:
                if not self.activated:
                    activation = self._wait_for_activation()
                    if not activation.get("activated"):
                        continue

                    command = str(activation.get("command", "") or "").strip()
                    if command:
                        self._execute_voice_command(command)
                        if self.running:
                            self.activated = True
                            self.state = "listening"
                        continue

                    self.activated = True
                    self.state = "active"
                    self._log("WAKE -> ACTIVE SESSION")
                    self._speak_activation_response()
                    if not self.running:
                        break

                    command = self._listen_active_command()
                    if command:
                        self._execute_voice_command(command)
                    if self.running:
                        self.activated = True
                        self.state = "listening"
                        self._log("READY FOR NEXT COMMAND")
                    continue

                command = self._listen_active_command()
                if not command:
                    continue

                self._execute_voice_command(command)
                if self.running and self.continuous_conversation:
                    self.activated = True
                    self.state = "listening"
                    self._log("CONTINUOUS SESSION -> LISTENING AGAIN")
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
