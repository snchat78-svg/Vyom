"""
Project : Vyom AI
Version : 1.1
Module  : Voice Controller

Purpose:
    Persistent voice interaction layer for Vyom AI.

Flow:

    Startup
       ↓
    TTS Startup Response
       ↓
    Microphone Session
       ↓
    Wake Word
       ↓
    ACTIVE Conversation
       ↓
    Command Listening
       ↓
    Speech-To-Text
       ↓
    Existing Executor / AutonomousAgent
       ↓
    Response
       ↓
    TTS
       ↓
    Command Listening Again

IMPORTANT:

    VoiceController is only the voice interaction layer.

    It does NOT duplicate:
        IntentEngine
        ToolManager
        AutonomousAgent
        SessionMemory

    Existing command execution pipeline remains unchanged.

Version 1.1 Fix:

    Wake word detection now explicitly transitions into
    active command listening.

    Flow:

        WAITING_FOR_WAKE
              ↓
        WAKE DETECTED
              ↓
        ACTIVE SESSION
              ↓
        LISTEN FOR COMMAND
              ↓
        EXECUTE
              ↓
        RESPONSE
              ↓
        LISTEN AGAIN

    The controller remains active after wake word and does
    not require "Vyom" before every command.
"""

import time
import difflib
import re

from .speech_to_text import SpeechToText
from .text_to_speech import TextToSpeech

from command_engine.executor import execute


class VoiceController:

    # =========================================================
    # INITIALIZATION
    # =========================================================

    def __init__(self):

        self.speech_to_text = (
            SpeechToText(
                preferred_language="hi-IN",
                fallback_language="en-IN",
                debug=True
            )
        )

        self.text_to_speech = (
            TextToSpeech(
                rate=165,
                volume=1.0,
                debug=True
            )
        )

        self.running = False

        self.state = "idle"

        self.activated = False

        self.continuous_conversation = True

        self.wake_words = (
            "vyom",
            "व्योम",
            "व्योम जी",
            "hey vyom",
            "हे व्योम"
        )

        self.wake_aliases = (
            "vyom",
            "व्योम",
            "व्योम जी",
            "hey vyom",
            "hey व्योम",
            "हे व्योम",
            "वियम",
            "वियॉम",
            "व्योम जी",
            "व्योमजी",
            "व्योम जि"
        )

    # =========================================================
    # DEBUG
    # =========================================================

    def _log(self, message):

        try:

            print(
                "[VOICE] "
                + str(message),
                flush=True
            )

        except Exception:
            pass

    # =========================================================
    # SAFE PRINT
    # =========================================================

    def _safe_print(self, message):

        try:

            print(
                message,
                flush=True
            )

        except Exception:
            pass

    # =========================================================
    # STATUS
    # =========================================================

    def is_available(self):

        return (
            self.speech_to_text.is_available()
        )

    def is_tts_available(self):

        return (
            self.text_to_speech.is_available()
        )

    # =========================================================
    # SPEAK
    # =========================================================

    def speak(self, text):

        self.state = "speaking"

        self._log(
            "TTS response started."
        )

        try:

            result = (
                self.text_to_speech.speak(
                    text
                )
            )

            if not isinstance(
                result,
                dict
            ):

                result = {
                    "success": bool(result)
                }

            self._log(
                "TTS response completed: "
                + str(
                    result.get(
                        "success",
                        False
                    )
                )
            )

            return result

        except Exception as error:

            self._log(
                "TTS ERROR: "
                + str(error)
            )

            return {
                "success": False,
                "message": str(error)
            }

    # =========================================================
    # WAKE NORMALIZATION
    # =========================================================

    def _normalize_wake_text(self, text):

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
    # COMPACT
    # =========================================================

    def _compact(self, text):

        return re.sub(
            r"\s+",
            "",
            self._normalize_wake_text(
                text
            )
        )

    # =========================================================
    # WAKE CANDIDATES
    # =========================================================

    def _wake_candidates(self):

        values = []

        for item in (
            self.wake_words
            + self.wake_aliases
        ):

            normalized = (
                self._normalize_wake_text(
                    item
                )
            )

            compact = (
                self._compact(
                    item
                )
            )

            if normalized:

                values.append(
                    normalized
                )

            if compact:

                values.append(
                    compact
                )

        result = []

        for value in values:

            if value not in result:

                result.append(
                    value
                )

        return result

    # =========================================================
    # IS WAKE WORD
    # =========================================================

    def _is_wake_word(self, text):

        normalized = (
            self._normalize_wake_text(
                text
            )
        )

        compact = self._compact(
            text
        )

        if not normalized:

            return False

        candidates = (
            self._wake_candidates()
        )

        if normalized in candidates:

            return True

        if compact in candidates:

            return True

        for candidate in candidates:

            if (
                len(candidate) >= 3
                and candidate in normalized
            ):

                return True

            if (
                len(candidate) >= 3
                and candidate in compact
            ):

                return True

        if len(normalized) <= 15:

            for candidate in candidates:

                if len(candidate) > 15:

                    continue

                ratio = difflib.SequenceMatcher(
                    None,
                    normalized,
                    candidate
                ).ratio()

                if ratio >= 0.78:

                    return True

        return False

    # =========================================================
    # FIND WAKE WORD
    # =========================================================

    def _find_wake_word(self, text):

        normalized = (
            self._normalize_wake_text(
                text
            )
        )

        if not normalized:

            return None

        for wake_word in self.wake_words:

            candidate = (
                self._normalize_wake_text(
                    wake_word
                )
            )

            if (
                candidate
                and candidate in normalized
            ):

                return candidate

        for alias in self.wake_aliases:

            candidate = (
                self._normalize_wake_text(
                    alias
                )
            )

            if (
                candidate
                and candidate in normalized
            ):

                return candidate

        return None

    # =========================================================
    # REMOVE WAKE WORD
    # =========================================================

    def _remove_wake_word(self, text):

        original = str(
            text or ""
        ).strip()

        if not original:

            return ""

        value = original

        for wake_word in (
            self.wake_words
            + self.wake_aliases
        ):

            pattern = re.compile(
                re.escape(
                    wake_word
                ),
                re.IGNORECASE
            )

            new_value = pattern.sub(
                " ",
                value,
                count=1
            )

            if new_value != value:

                value = new_value

                break

        return re.sub(
            r"\s+",
            " ",
            value
        ).strip()

    # =========================================================
    # ACTIVATE
    # =========================================================

    def _activate(self):

        self.activated = True

        self.state = "active"

        self._log(
            "WAKE WORD DETECTED."
        )

        self._log(
            "Voice session ACTIVE."
        )

        self._log(
            "STATE TRANSITION: "
            "WAITING_FOR_WAKE -> ACTIVE"
        )

    # =========================================================
    # PROCESS TEXT
    # =========================================================

    def process_text(self, text):

        text = str(
            text or ""
        ).strip()

        if not text:

            return {
                "success": False,
                "text": "",
                "message": "No command received.",
                "result": None
            }

        self.state = "processing"

        self._log(
            "Processing command: "
            + text
        )

        try:

            result = execute(
                text
            )

            if isinstance(
                result,
                dict
            ):

                success = result.get(
                    "success",
                    True
                )

                message = result.get(
                    "message",
                    result.get(
                        "text",
                        str(result)
                    )
                )

            else:

                success = True

                message = str(
                    result
                )

            self._log(
                "Execution completed."
            )

            return {
                "success": bool(
                    success
                ),
                "text": text,
                "message": str(
                    message
                ),
                "result": result
            }

        except Exception as error:

            self._log(
                "Execution error: "
                + str(error)
            )

            return {
                "success": False,
                "text": text,
                "message": (
                    "Command execution failed: "
                    + str(error)
                ),
                "result": None
            }

    # =========================================================
    # LISTEN ONCE
    # =========================================================

    def listen_once(
        self,
        announce=True,
        timeout=5,
        phrase_time_limit=8,
        wake_mode=None
    ):

        self._log(
            "STT listen_once() START"
        )

        try:

            result = (
                self.speech_to_text.listen(
                    timeout=timeout,
                    phrase_time_limit=phrase_time_limit,
                    announce=announce,
                    wake_mode=wake_mode
                )
            )

        except Exception as error:

            self._log(
                "STT listen_once() ERROR: "
                + str(error)
            )

            return {
                "success": False,
                "status": "error",
                "text": "",
                "message": str(error)
            }

        if not isinstance(
            result,
            dict
        ):

            result = {
                "success": bool(result),
                "status": "unknown",
                "text": ""
            }

        self._log(
            "STT listen_once() COMPLETE: "
            + str(
                result.get(
                    "status",
                    ""
                )
            )
        )

        return result

    # =========================================================
    # WAIT FOR ACTIVATION
    # =========================================================

    def _wait_for_activation(self):

        self.state = "waiting_for_wake"

        self._log(
            "WAITING_FOR_WAKE"
        )

        result = self.listen_once(
            announce=False,
            timeout=2.5,
            phrase_time_limit=4,
            wake_mode=True
        )

        if not result.get(
            "success",
            False
        ):

            status = result.get(
                "status",
                ""
            )

            if status == "silence":

                self._log(
                    "Wake listen: silence."
                )

            elif status == "device_error":

                self._log(
                    "Wake listen: device error."
                )

            elif status == "wake_not_detected":

                self._log(
                    "Wake word not detected."
                )

            else:

                self._log(
                    "Wake listen status: "
                    + str(status)
                )

            return {
                "activated": False,
                "command": "",
                "wake_word": None,
                "text": ""
            }

        text = str(
            result.get(
                "text",
                ""
            )
        ).strip()

        self._safe_print(
            "Wake speech -> "
            + text
        )

        wake_word = (
            self._find_wake_word(
                text
            )
        )

        if not wake_word:

            self._log(
                "Recognized speech but no wake word."
            )

            return {
                "activated": False,
                "command": "",
                "wake_word": None,
                "text": text
            }

        self._activate()

        command = (
            self._remove_wake_word(
                text
            )
        )

        self._safe_print(
            "Wake word detected -> "
            + str(wake_word)
        )

        if command:

            self._safe_print(
                "Command after wake -> "
                + command
            )

        return {
            "activated": True,
            "command": command,
            "wake_word": wake_word,
            "text": text
        }

    # =========================================================
    # ACTIVE COMMAND
    # =========================================================

    def _listen_active_command(self):

        self.state = "listening"

        self._log(
            "=================================================="
        )

        self._log(
            "ACTIVE COMMAND LISTENING"
        )

        self._log(
            "STATE = ACTIVE"
        )

        self._log(
            "Waiting for user's command..."
        )

        self._safe_print(
            ""
        )

        self._safe_print(
            "Vyom : Listening for your command..."
        )

        result = self.listen_once(
            announce=False,
            timeout=5,
            phrase_time_limit=8,
            wake_mode=False
        )

        if not result.get(
            "success",
            False
        ):

            status = result.get(
                "status",
                ""
            )

            self._log(
                "Active listen failed: "
                + str(status)
            )

            return ""

        command = str(
            result.get(
                "text",
                ""
            )
        ).strip()

        if command:

            self._safe_print(
                "Command detected -> "
                + command
            )

            self._log(
                "ACTIVE COMMAND RECEIVED"
            )

        else:

            self._log(
                "Active command was empty."
            )

        return command

    # =========================================================
    # EXIT COMMAND
    # =========================================================

    def _is_exit_command(self, text):

        value = (
            self._normalize_wake_text(
                text
            )
        )

        exit_commands = (
            "exit",
            "quit",
            "stop listening",
            "shutdown voice",
            "bye",
            "goodbye",
            "बंद हो जाओ",
            "बंद करो",
            "रुक जाओ",
            "रुक जाओ व्योम",
            "बाय",
            "अलविदा"
        )

        normalized_commands = [
            self._normalize_wake_text(
                item
            )
            for item in exit_commands
        ]

        return value in normalized_commands

    # =========================================================
    # SPEAK RESPONSE
    # =========================================================

    def _speak_response(self, response):

        response = str(
            response or ""
        ).strip()

        if not response:

            self.state = "listening"

            return

        self._safe_print(
            "Vyom : "
            + response
        )

        self.speak(
            response
        )

        # Allow old Windows audio driver to release
        # the speaker before opening another STT cycle.

        time.sleep(
            0.35
        )

        if self.running:

            self.state = "listening"

    # =========================================================
    # STARTUP RESPONSE
    # =========================================================

    def _speak_startup_response(self):

        self._log(
            "STARTUP TTS BEGIN"
        )

        response = (
            "नमस्ते, मैं व्योम हूँ। "
            "मुझे जगाने के लिए व्योम कहिए।"
        )

        result = self.speak(
            response
        )

        self._log(
            "STARTUP TTS END: "
            + str(
                result.get(
                    "success",
                    False
                )
            )
        )

        time.sleep(
            0.35
        )

        return result

    # =========================================================
    # ACTIVATION RESPONSE
    # =========================================================

    def _speak_activation_response(self):

        self._log(
            "ACTIVATION RESPONSE BEGIN"
        )

        self._speak_response(
            "हाँ, बताइए।"
        )

        self._log(
            "ACTIVATION RESPONSE END"
        )

    # =========================================================
    # EXECUTE VOICE COMMAND
    # =========================================================

    def _execute_voice_command(self, command):

        command = str(
            command or ""
        ).strip()

        if not command:

            self._log(
                "Empty command received."
            )

            return {
                "success": False,
                "text": "",
                "message": "",
                "result": None
            }

        if self._is_exit_command(
            command
        ):

            self._log(
                "Exit command detected."
            )

            self._speak_response(
                "ठीक है। मैं सुनना बंद कर रहा हूँ।"
            )

            self.activated = False

            self.running = False

            self.state = "idle"

            return {
                "success": True,
                "text": command,
                "message": "Voice session stopped.",
                "result": None
            }

        self._safe_print(
            "Processing -> "
            + command
        )

        self._log(
            "Sending command to existing executor..."
        )

        result = self.process_text(
            command
        )

        message = str(
            result.get(
                "message",
                ""
            )
            or ""
        ).strip()

        if message:

            self._speak_response(
                message
            )

        else:

            self._safe_print(
                "Vyom : Command completed."
            )

        return result

    # =========================================================
    # RUN
    # =========================================================

    def run(self):

        self._safe_print(
            "=" * 60
        )

        self._safe_print(
            "Vyom AI - Voice Engine v1.1"
        )

        self._safe_print(
            "=" * 60
        )

        self._safe_print(
            ""
        )

        self._log(
            "VOICE ENGINE STARTING..."
        )

        # =====================================================
        # STT AVAILABILITY
        # =====================================================

        if not self.speech_to_text.is_available():

            self._safe_print(
                "Vyom : Speech-To-Text is not available."
            )

            self._safe_print(
                "Reason : "
                + self.speech_to_text.error_message
            )

            return False

        # =====================================================
        # TTS AVAILABILITY
        # =====================================================

        if not self.text_to_speech.is_available():

            self._safe_print(
                "Vyom : Text-To-Speech is not available."
            )

            self._safe_print(
                "Reason : "
                + self.text_to_speech.error_message
            )

        self.running = True

        self.activated = False

        self.state = "idle"

        try:

            # =================================================
            # WINDOWS 8 SAFE STARTUP ORDER
            # =================================================
            #
            # 1. TTS
            # 2. TTS completely finishes
            # 3. Microphone starts
            # 4. Wake detection
            # =================================================

            if self.text_to_speech.is_available():

                self._speak_startup_response()

            else:

                self._safe_print(
                    "Vyom : Voice output unavailable."
                )

            # =================================================
            # START MICROPHONE
            # =================================================

            self._log(
                "Starting microphone AFTER startup TTS..."
            )

            if not self.speech_to_text.start_session():

                self._safe_print(
                    "Vyom : Microphone could not be started."
                )

                return False

            self._safe_print(
                ""
            )

            self._safe_print(
                "Vyom : Voice engine is ready."
            )

            self._safe_print(
                "Vyom : Say 'Vyom' to activate."
            )

            self._safe_print(
                ""
            )

            # =================================================
            # MAIN VOICE LOOP
            # =================================================

            while self.running:

                # =================================================
                # WAITING FOR WAKE
                # =================================================

                if not self.activated:

                    self._log(
                        "MAIN LOOP -> WAITING_FOR_WAKE"
                    )

                    activation = (
                        self._wait_for_activation()
                    )

                    if not activation.get(
                        "activated",
                        False
                    ):

                        continue

                    # -------------------------------------------------
                    # WAKE DETECTED
                    # -------------------------------------------------

                    command = str(
                        activation.get(
                            "command",
                            ""
                        )
                        or ""
                    ).strip()

                    self._log(
                        "MAIN LOOP -> WAKE DETECTED"
                    )

                    self._log(
                        "Activation command = "
                        + (
                            command
                            if command
                            else "<empty>"
                        )
                    )

                    # =================================================
                    # CASE 1
                    # "Vyom Excel kholo"
                    #
                    # Wake word + command in same sentence.
                    # =================================================

                    if command:

                        self._log(
                            "Wake + command detected."
                        )

                        self._execute_voice_command(
                            command
                        )

                        if self.running:

                            self.activated = True

                            self.state = "listening"

                            self._log(
                                "Conversation remains ACTIVE."
                            )

                        continue

                    # =================================================
                    # CASE 2
                    # User only says:
                    #
                    # "Vyom"
                    #
                    # IMPORTANT:
                    # Immediately enter active command listening.
                    # =================================================

                    self._log(
                        "Wake word only detected."
                    )

                    self._log(
                        "TRANSITION: "
                        "WAKE -> ACTIVE COMMAND LISTENING"
                    )

                    self.activated = True

                    self.state = "active"

                    self._safe_print(
                        "Vyom : हाँ, बताइए।"
                    )

                    # -------------------------------------------------
                    # Small delay after wake detection.
                    #
                    # This prevents the next microphone capture from
                    # accidentally capturing the wake detection audio.
                    # -------------------------------------------------

                    time.sleep(
                        0.30
                    )

                    # =================================================
                    # IMPORTANT FIX
                    #
                    # Do NOT depend on another outer-loop cycle here.
                    #
                    # Immediately start command listening.
                    # =================================================

                    self._log(
                        "STARTING ACTIVE COMMAND LISTENER NOW..."
                    )

                    command = (
                        self._listen_active_command()
                    )

                    self._log(
                        "ACTIVE COMMAND LISTENER RETURNED."
                    )

                    if command:

                        self._execute_voice_command(
                            command
                        )

                    else:

                        self._log(
                            "No command received after wake."
                        )

                    # -------------------------------------------------
                    # Stay active for next command.
                    # -------------------------------------------------

                    if self.running:

                        self.activated = True

                        self.state = "listening"

                        self._log(
                            "Conversation remains ACTIVE."
                        )

                    continue

                # =================================================
                # ACTIVE CONVERSATION
                # =================================================

                self._log(
                    "MAIN LOOP -> ACTIVE CONVERSATION"
                )

                self.activated = True

                self.state = "listening"

                command = (
                    self._listen_active_command()
                )

                if not command:

                    self._log(
                        "No command received."
                    )

                    continue

                # =================================================
                # EXECUTE
                # =================================================

                result = (
                    self._execute_voice_command(
                        command
                    )
                )

                # =================================================
                # EXIT
                # =================================================

                if self._is_exit_command(
                    command
                ):

                    self._log(
                        "Voice session exit requested."
                    )

                    break

                # =================================================
                # CONTINUOUS CONVERSATION
                # =================================================

                if (
                    self.continuous_conversation
                    and self.running
                ):

                    self.activated = True

                    self.state = "listening"

                    self._log(
                        "Conversation remains ACTIVE."
                    )

                    self._log(
                        "Ready for next command."
                    )

                else:

                    self.activated = False

                    self.state = "waiting_for_wake"

                    self._log(
                        "Conversation ended. "
                        "Returning to wake mode."
                    )

        except KeyboardInterrupt:

            self._log(
                "KeyboardInterrupt received."
            )

        except Exception as error:

            self._log(
                "=================================================="
            )

            self._log(
                "VOICE ENGINE ERROR"
            )

            self._log(
                str(error)
            )

            self._safe_print(
                "Vyom Voice Error : "
                + str(error)
            )

        finally:

            self.running = False

            self.activated = False

            self.state = "idle"

            self._log(
                "Cleaning up voice resources..."
            )

            try:

                self.speech_to_text.stop_session()

            except Exception as error:

                self._log(
                    "STT cleanup error: "
                    + str(error)
                )

            try:

                self.text_to_speech.stop()

            except Exception as error:

                self._log(
                    "TTS cleanup error: "
                    + str(error)
                )

            self._log(
                "VOICE ENGINE STOPPED."
            )

        return True

    # =========================================================
    # STOP
    # =========================================================

    def stop(self):

        self._log(
            "Stop requested."
        )

        self.running = False

        self.activated = False

        self.state = "idle"

        try:

            self.text_to_speech.stop()

        except Exception:
            pass

        try:

            self.speech_to_text.stop_session()

        except Exception:
            pass


# =============================================================
# STANDALONE
# =============================================================

def main():

    controller = VoiceController()

    controller.run()


if __name__ == "__main__":

    main()
