"""Vyom AI - persistent voice conversation controller.

The session is persistent, but the physical microphone is opened only during
an individual capture. This avoids Windows audio contention with SAPI/pyttsx3
while preserving fully automatic, push-to-talk-free conversation.
"""

import difflib
import re
import sys
import time

from .romanizer import normalize_voice_text
from .speech_to_text import SpeechToText
from .text_to_speech import TextToSpeech
from ai_core.conversation_manager import ConversationManager


class VoiceController:
    BUILD_ID = "VYOM_VOICE_HANDOFF_V17_FINAL"

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
            "hey vyom", "हे व्योम", "हे वियोम", "vyom ji", "व्योम जी",
            "vyom", "व्योम", "viyom", "viom", "वियोम", "वियम", "वियॉम",
            "vyam", "veom", "vyoam", "viyam", "biom", "beyom", "vyoum",
            "व्यम", "ब्योम", "बायोम", "व्योमजी", "व्योम जि",
        )

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
                text = text.encode("unicode_escape", errors="backslashreplace").decode("ascii")
            stream.write(text + "\n")
            stream.flush()
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

        # Voice boundary contract: downstream receives Roman/Latin text.
        # Keep the original STT transcript separately for diagnostics.
        result = dict(result)
        raw_text = str(result.get("raw_text") or result.get("text") or "").strip()
        result["raw_text"] = raw_text
        result["text"] = normalize_voice_text(str(result.get("text") or raw_text).strip())

        self.last_listen_status = str(result.get("status", ""))
        self._log("STT listen_once returned: status=%s success=%s text_length=%d" % (
            self.last_listen_status, bool(result.get("success")), len(str(result.get("text", "") or ""))
        ))
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

        # A fuzzy wake match can produce an alias such as "vyam" for a
        # transcript such as "vyayam".  That is still the wake utterance,
        # not a user command; do not send it into the Executor.
        if command == text and wake_word and len(self._normalize(text)) <= 24:
            try:
                score = difflib.SequenceMatcher(
                    None,
                    self._normalize(text).replace(" ", ""),
                    self._normalize(wake_word).replace(" ", "")
                ).ratio()
                if score >= 0.72:
                    command = ""
                    self._log("Wake-only utterance consumed after fuzzy match (%.2f)." % score)
            except Exception:
                pass

        if command:
            self._safe_print("Command after wake -> " + command)
        else:
            self._log("WAKE ACTIVATION ONLY -> waiting for command")
        return {"activated": True, "command": command, "wake_word": wake_word or "Vyom", "text": text}

    def _listen_active_command(self):
        self.state = "listening"
        self._log("STATE -> LISTENING")
        self._safe_print("Vyom : Listening for your command...")

        try:
            result = self.listen_once(
                announce=False,
                timeout=8,
                phrase_time_limit=None,
                wake_mode=False,
            )
        except Exception as error:
            self._log("ACTIVE LISTEN EXCEPTION: " + str(error))
            return ""

        try:
            if not isinstance(result, dict):
                self._log("ACTIVE LISTEN INVALID RESULT: " + type(result).__name__)
                return ""

            status = str(result.get("status", "") or "").strip().lower()
            text_value = result.get("text", "")
            command = str(text_value or "").strip()
            success = bool(result.get("success"))
            self.last_listen_status = status

            self._log(
                "ACTIVE LISTEN DECISION: status=%s success=%s text_length=%d"
                % (status, success, len(command))
            )

            if status == "device_error":
                self._recover_microphone()
                return ""

            # A recognized status with non-empty text is a valid command even
            # when a third-party/mocked STT wrapper reports success=False.
            if not command:
                self._log("ACTIVE COMMAND EMPTY -> LISTEN AGAIN")
                return ""

            if not success and status not in {"recognized", "success"}:
                self._log("ACTIVE LISTEN NON-RECOGNIZED: " + status)
                return ""

            # IMPORTANT: do not perform Unicode stdout I/O here. The previous
            # runtime stopped immediately after `listen_once returned` when
            # the recognized Devanagari command was printed. The command must
            # reach the executor before any optional console presentation.
            safe_command = command.encode("unicode_escape", errors="backslashreplace").decode("ascii")
            self._log("ACTIVE COMMAND RECEIVED: " + safe_command)
            self._log("ACTIVE COMMAND HANDOFF -> EXECUTOR")
            return command

        except Exception as error:
            self._log("ACTIVE COMMAND HANDOFF EXCEPTION: " + str(error))
            return ""

    def _is_exit_command(self, text):
        value = self._normalize(text)
        return value in {
            "exit", "quit", "stop listening", "shutdown voice", "bye", "goodbye", "stop",
            "बंद हो जाओ", "बंद करो", "रुक जाओ", "रुक जाओ व्योम", "सुनना बंद करो", "बाय", "अलविदा",
        }

    def _speak_response(self, response):
        message = str(response or "").strip()
        if not message:
            self.state = "listening"
            return {"success": True, "text": "", "message": ""}

        self._log("TTS HANDOFF: physical microphone is already released.")
        self._log("TTS HANDOFF BEGIN")
        result = self.speak(message)
        self._log("TTS HANDOFF END")

        if self.running:
            time.sleep(0.30)
            self.state = "listening"
            self._log("READY TO LISTEN AGAIN")
        return result

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

        safe_command = command.encode("unicode_escape", errors="backslashreplace").decode("ascii")
        self._log("DISPATCHING VOICE COMMAND: " + safe_command)
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
        self._safe_print("Vyom AI - Voice Engine v17.0")
        self._safe_print("=" * 60)
        self._log("VOICE ENGINE STARTING...")
        self._log("BUILD SIGNATURE: " + self.BUILD_ID)

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


