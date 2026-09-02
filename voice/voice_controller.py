# ============================================================
# Project : Vyom AI
# Module  : voice_controller.py
# Version : 0.5
#
# Purpose:
#     Controlled continuous voice interface for Vyom AI.
#
# Voice State:
#
#     IDLE
#       ↓
#     WAKE / ACTIVATION
#       ↓
#     LISTENING
#       ↓
#     PROCESSING
#       ↓
#     EXECUTION
#       ↓
#     SPEAKING
#       ↓
#     LISTENING
#       ↓
#     ...
#       ↓
#     EXIT
#
# IMPORTANT:
#
#     Existing Executor / AutonomousAgent / ToolManager
#     integration is preserved.
#
#     This module does NOT duplicate IntentEngine logic.
#
#     Step 1:
#         Wake Word + Continuous Conversation
#
#     Existing SessionMemory is preserved through the
#     persistent Executor / AutonomousAgent.
# ============================================================

import time
import difflib

from voice.speech_to_text import SpeechToText
from voice.text_to_speech import TextToSpeech
from command_engine.executor import execute


# ============================================================
# SAFE PRINT
# ============================================================

def _safe_print(*args, **kwargs):

    try:

        print(
            *args,
            **kwargs
        )

    except (
        PermissionError,
        OSError
    ):

        pass

    except Exception:

        pass


# ============================================================
# VOICE CONTROLLER
# ============================================================

class VoiceController:

    # ========================================================
    # INITIALIZATION
    # ========================================================

    def __init__(
        self,
        wake_words=None
    ):

        self.speech_to_text = SpeechToText()

        self.text_to_speech = TextToSpeech()

        self.running = False

        # ----------------------------------------------------
        # Voice state
        # ----------------------------------------------------

        self.state = "idle"

        # ----------------------------------------------------
        # Wake words
        #
        # Hindi + English variants.
        # ----------------------------------------------------

        if wake_words is None:

            wake_words = [
                "vyom",
                "व्योम",
                "व्योम जी",
                "hey vyom",
                "हे व्योम"
            ]

        self.wake_words = [
            str(word).strip().lower()
            for word in wake_words
            if str(word).strip()
        ]

        # ----------------------------------------------------
        # Common speech-recognition variations.
        #
        # These are NOT commands.
        # They are only used for wake-word recognition.
        # ----------------------------------------------------

        self.wake_aliases = [
            # Main forms
            "vyom",
            "व्योम",
            "व्योम जी",
            "hey vyom",
            "हे व्योम",

            # English STT variations
            "viyom",
            "veyom",
            "veyam",
            "vyam",
            "viom",
            "vyom ji",
            "hey viyom",
            "hey veyom",

            # Hindi STT variations
            "वियॉम",
            "वियोम",
            "वियॉम जी",
            "वियोम जी",
            "व्योमजी",
            "हेव्योम",
            "हे वियोम",
            "हे वियॉम"
        ]

        # ----------------------------------------------------
        # Activation mode
        # ----------------------------------------------------

        self.activated = False

        # ----------------------------------------------------
        # Continuous conversation
        #
        # Once activated, Vyom remains active until an
        # explicit voice-mode exit command is received.
        # ----------------------------------------------------

        self.continuous_conversation = True

    # ========================================================
    # STATUS
    # ========================================================

    def is_available(self):

        return self.speech_to_text.is_available()

    # ========================================================
    # TTS STATUS
    # ========================================================

    def is_tts_available(self):

        return self.text_to_speech.is_available()

    # ========================================================
    # SPEAK
    # ========================================================

    def speak(
        self,
        text
    ):

        return self.text_to_speech.speak(
            text
        )

    # ========================================================
    # NORMALIZE WAKE TEXT
    # ========================================================

    @staticmethod
    def _normalize_wake_text(
        text
    ):

        value = str(
            text or ""
        ).strip().lower()

        if not value:
            return ""

        # ----------------------------------------------------
        # Remove common punctuation.
        # ----------------------------------------------------

        for char in (
            ",",
            ".",
            "!",
            "?",
            ":",
            ";",
            "-",
            "_",
            "'",
            '"',
            "`"
        ):

            value = value.replace(
                char,
                " "
            )

        # ----------------------------------------------------
        # Normalize multiple spaces.
        # ----------------------------------------------------

        value = " ".join(
            value.split()
        )

        return value

    # ========================================================
    # WAKE WORD CHECK
    # ========================================================

    def _is_wake_word(
        self,
        text
    ):

        value = self._normalize_wake_text(
            text
        )

        if not value:
            return False

        # ----------------------------------------------------
        # Exact wake words.
        # ----------------------------------------------------

        for wake_word in self.wake_words:

            normalized = (
                self._normalize_wake_text(
                    wake_word
                )
            )

            if value == normalized:

                return True

        # ----------------------------------------------------
        # Exact aliases.
        # ----------------------------------------------------

        for alias in self.wake_aliases:

            normalized = (
                self._normalize_wake_text(
                    alias
                )
            )

            if value == normalized:

                return True

        # ----------------------------------------------------
        # Short fuzzy matching.
        #
        # Only short phrases are eligible.
        # This prevents a normal long command from
        # accidentally becoming a wake word.
        # ----------------------------------------------------

        if len(value) <= 15:

            candidates = []

            candidates.extend(
                self.wake_words
            )

            candidates.extend(
                self.wake_aliases
            )

            for candidate in candidates:

                candidate_value = (
                    self._normalize_wake_text(
                        candidate
                    )
                )

                if not candidate_value:
                    continue

                ratio = difflib.SequenceMatcher(
                    None,
                    value,
                    candidate_value
                ).ratio()

                if ratio >= 0.78:

                    return True

        return False

    # ========================================================
    # FIND WAKE WORD INSIDE SENTENCE
    # ========================================================

    def _find_wake_word(
        self,
        text
    ):

        value = self._normalize_wake_text(
            text
        )

        if not value:
            return None

        # ----------------------------------------------------
        # Exact sentence = wake word.
        # ----------------------------------------------------

        if self._is_wake_word(
            value
        ):

            return value

        # ----------------------------------------------------
        # Build unique candidates.
        # ----------------------------------------------------

        candidates = []

        for candidate in (
            list(self.wake_words)
            + list(self.wake_aliases)
        ):

            normalized = (
                self._normalize_wake_text(
                    candidate
                )
            )

            if (
                normalized
                and
                normalized not in candidates
            ):

                candidates.append(
                    normalized
                )

        # ----------------------------------------------------
        # Longest candidates first.
        #
        # Prevents "vyom" from matching before
        # "vyom ji".
        # ----------------------------------------------------

        candidates.sort(
            key=len,
            reverse=True
        )

        # ----------------------------------------------------
        # Wake word at beginning of sentence.
        #
        # Examples:
        #
        #     "vyom open notepad"
        #     "hey vyom open chrome"
        # ----------------------------------------------------

        for candidate in candidates:

            if value.startswith(
                candidate + " "
            ):

                return candidate

        # ----------------------------------------------------
        # Wake word somewhere inside a short sentence.
        #
        # Restricted to short input to avoid normal commands
        # accidentally activating Vyom.
        # ----------------------------------------------------

        if len(value) <= 40:

            words = value.split()

            for index, word in enumerate(words):

                if self._is_wake_word(
                    word
                ):

                    return word

                # --------------------------------------------
                # Check two-word wake phrases.
                # --------------------------------------------

                if index + 1 < len(words):

                    two_words = (
                        words[index]
                        + " "
                        + words[index + 1]
                    )

                    if self._is_wake_word(
                        two_words
                    ):

                        return two_words

        return None

    # ========================================================
    # REMOVE WAKE WORD FROM COMMAND
    # ========================================================

    def _remove_wake_word(
        self,
        text
    ):

        original = str(
            text or ""
        ).strip()

        if not original:

            return ""

        normalized = (
            self._normalize_wake_text(
                original
            )
        )

        if not normalized:

            return ""

        # ----------------------------------------------------
        # Exact wake word.
        # ----------------------------------------------------

        if self._is_wake_word(
            normalized
        ):

            return ""

        # ----------------------------------------------------
        # Build unique candidates.
        # ----------------------------------------------------

        candidates = []

        for candidate in (
            list(self.wake_words)
            + list(self.wake_aliases)
        ):

            candidate_value = (
                self._normalize_wake_text(
                    candidate
                )
            )

            if (
                candidate_value
                and
                candidate_value not in candidates
            ):

                candidates.append(
                    candidate_value
                )

        # ----------------------------------------------------
        # Longest first.
        # ----------------------------------------------------

        candidates.sort(
            key=len,
            reverse=True
        )

        # ----------------------------------------------------
        # Remove wake word from beginning.
        # ----------------------------------------------------

        for candidate_value in candidates:

            if normalized == candidate_value:

                return ""

            if normalized.startswith(
                candidate_value + " "
            ):

                return normalized[
                    len(candidate_value):
                ].strip()

        return original.strip()

    # ========================================================
    # ACTIVATE
    # ========================================================

    def _activate(self):

        self.activated = True

        self.state = "listening"

        _safe_print(
            "Vyom : Listening for your command..."
        )

        _safe_print(
            "Vyom : Wake word detected. Voice conversation activated."
        )

    # ========================================================
    # DEACTIVATE
    # ========================================================

    def _deactivate(self):

        self.activated = False

        self.state = "idle"

    # ========================================================
    # PROCESS TEXT COMMAND
    # ========================================================

    def process_text(
        self,
        text
    ):

        if text is None:

            return {
                "success": False,
                "text": "",
                "message": (
                    "No command was received."
                ),
                "result": None
            }

        text = str(
            text
        ).strip()

        if not text:

            return {
                "success": False,
                "text": "",
                "message": (
                    "No command was received."
                ),
                "result": None
            }

        # ----------------------------------------------------
        # PROCESSING STATE
        # ----------------------------------------------------

        self.state = "processing"

        try:

            result = execute(
                text
            )

            return {
                "success": True,
                "text": text,
                "message": str(
                    result
                ),
                "result": result
            }

        except Exception as error:

            return {
                "success": False,
                "text": text,
                "message": (
                    "Command execution failed: "
                    + str(error)
                ),
                "result": None
            }

    # ========================================================
    # LISTEN ONCE
    # ========================================================

    def listen_once(
        self,
        announce=False,
        timeout=4,
        phrase_time_limit=7
    ):

        if not self.is_available():

            return {
                "success": False,
                "status": "unavailable",
                "text": "",
                "message": (
                    "Speech recognition is not available: "
                    + self.speech_to_text.error_message
                ),
                "result": None
            }

        try:

            speech_result = (
                self.speech_to_text.listen(
                    timeout=timeout,
                    phrase_time_limit=phrase_time_limit,
                    announce=announce
                )
            )

        except Exception as error:

            return {
                "success": False,
                "status": "error",
                "text": "",
                "message": str(error),
                "result": None
            }

        if speech_result.get(
            "status"
        ) == "silence":

            return {
                "success": False,
                "status": "silence",
                "text": "",
                "message": "",
                "result": None
            }

        if not speech_result.get(
            "success",
            False
        ):

            return {
                "success": False,
                "status": speech_result.get(
                    "status",
                    "error"
                ),
                "text": "",
                "message": speech_result.get(
                    "message",
                    ""
                ),
                "result": None
            }

        text = speech_result.get(
            "text",
            ""
        ).strip()

        if not text:

            return {
                "success": False,
                "status": "silence",
                "text": "",
                "message": "",
                "result": None
            }

        _safe_print(
            "You : " + text
        )

        return {
            "success": True,
            "status": "recognized",
            "text": text,
            "message": text,
            "result": None
        }

    # ========================================================
    # WAIT FOR WAKE WORD
    # ========================================================

    def _wait_for_activation(self):

        self.state = "idle"

        result = self.listen_once(
            announce=False,
            timeout=2.5,
            phrase_time_limit=4
        )

        if not result.get(
            "success",
            False
        ):

            status = result.get(
                "status",
                ""
            )

            # ------------------------------------------------
            # Keep voice mode alive for temporary
            # recognition/service failures.
            # ------------------------------------------------

            if status in (
                "service_error",
                "service_timeout",
                "device_error",
                "error"
            ):

                message = result.get(
                    "message",
                    ""
                )

                if message:

                    _safe_print(
                        "Vyom : " + message
                    )

            return False

        text = result.get(
            "text",
            ""
        ).strip()

        if not text:

            return False

        # ----------------------------------------------------
        # Show exactly what STT returned.
        #
        # This is important for diagnosing wake-word
        # recognition problems.
        # ----------------------------------------------------

        _safe_print(
            "Vyom : Wake check -> " + text
        )

        # ----------------------------------------------------
        # Detect wake word.
        # ----------------------------------------------------

        wake_word = self._find_wake_word(
            text
        )

        if wake_word is None:

            return False

        # ----------------------------------------------------
        # ACTIVATE
        # ----------------------------------------------------

        self._activate()

        _safe_print(
            "Vyom : Wake word detected -> "
            + wake_word
        )

        # ----------------------------------------------------
        # Remove wake word.
        # ----------------------------------------------------

        command = self._remove_wake_word(
            text
        )

        # ----------------------------------------------------
        # Wake + command in same sentence.
        #
        # Example:
        #
        #     "Vyom open notepad"
        # ----------------------------------------------------

        if command:

            return command

        # ----------------------------------------------------
        # Only wake word was spoken.
        # ----------------------------------------------------

        return True

    # ========================================================
    # LISTEN FOR ACTIVE COMMAND
    # ========================================================

    def _listen_active_command(self):

        self.state = "listening"

        result = self.listen_once(
            announce=True,
            timeout=5,
            phrase_time_limit=8
        )

        if not result.get(
            "success",
            False
        ):

            return None

        text = result.get(
            "text",
            ""
        ).strip()

        if not text:

            return None

        return text

    # ========================================================
    # CHECK EXIT COMMAND
    # ========================================================

    @staticmethod
    def _is_exit_command(
        command
    ):

        command_lower = (
            str(
                command or ""
            )
            .lower()
            .strip()
        )

        return command_lower in (
            "exit",
            "quit",
            "stop voice",
            "stop voice mode",
            "close voice",
            "close voice mode",
            "exit voice",
            "exit voice mode",
            "वॉइस बंद",
            "वॉयस बंद",
            "बंद करो",
            "वॉइस बंद करो",
            "वॉयस बंद करो",
            "वॉइस मोड बंद करो",
            "वॉयस मोड बंद करो",
            "वॉइस मोड बंद",
            "वॉयस मोड बंद"
        )

    # ========================================================
    # SPEAK RESPONSE
    # ========================================================

    def _speak_response(
        self,
        response
    ):

        if not response:

            return

        self.state = "speaking"

        _safe_print(
            "Vyom : " + str(
                response
            )
        )

        try:

            self.speak(
                response
            )

        except Exception as error:

            _safe_print(
                "Vyom : Voice output error: "
                + str(error)
            )

        # ----------------------------------------------------
        # Small audio handoff delay.
        #
        # This helps prevent the microphone from immediately
        # capturing the tail end of Vyom's own speech.
        # ----------------------------------------------------

        time.sleep(
            0.25
        )

    # ========================================================
    # EXECUTE ACTIVE COMMAND
    # ========================================================

    def _execute_voice_command(
        self,
        command
    ):

        if not command:

            return False

        command = str(
            command
        ).strip()

        if not command:

            return False

        # ----------------------------------------------------
        # EXIT
        # ----------------------------------------------------

        if self._is_exit_command(
            command
        ):

            self.running = False

            self.state = "speaking"

            response = (
                "ठीक है, voice mode बंद कर रहा हूँ।"
            )

            _safe_print(
                "Vyom : " + response
            )

            try:

                self.speak(
                    response
                )

            except Exception:

                pass

            return True

        # ----------------------------------------------------
        # PROCESS COMMAND
        # ----------------------------------------------------

        self.state = "processing"

        _safe_print(
            "Vyom : Processing command..."
        )

        result = self.process_text(
            command
        )

        # ----------------------------------------------------
        # SPEAK RESULT
        # ----------------------------------------------------

        response = result.get(
            "message",
            ""
        )

        if response:

            self._speak_response(
                response
            )

        return True

    # ========================================================
    # RUN VOICE MODE
    # ========================================================

    def run(self):

        if not self.is_available():

            _safe_print(
                "Vyom : Voice input is not available."
            )

            _safe_print(
                "Reason : "
                + self.speech_to_text.error_message
            )

            return

        self.running = True

        self.state = "idle"

        self.activated = False

        _safe_print("")

        _safe_print(
            "=" * 60
        )

        _safe_print(
            "Vyom AI - Voice Assistant"
        )

        _safe_print(
            "=" * 60
        )

        _safe_print("")

        _safe_print(
            "Vyom : Say 'Vyom' when you want me."
        )

        _safe_print(
            "Vyom : After activation, you can keep speaking."
        )

        _safe_print(
            "Vyom : Say 'exit' to close voice mode."
        )

        _safe_print("")

        # ----------------------------------------------------
        # Persistent microphone session
        # ----------------------------------------------------

        if not self.speech_to_text.start_session():

            _safe_print(
                "Vyom : I could not start the microphone."
            )

            _safe_print(
                "Reason : "
                + self.speech_to_text.error_message
            )

            self.running = False

            return

        try:

            while self.running:

                # =================================================
                # IDLE / WAKE DETECTION
                # =================================================

                if not self.activated:

                    wake_result = (
                        self._wait_for_activation()
                    )

                    # ---------------------------------------------
                    # No wake word yet.
                    # ---------------------------------------------

                    if not wake_result:

                        continue

                    # ---------------------------------------------
                    # Wake word + command.
                    #
                    # Example:
                    #
                    #     "Vyom open notepad"
                    # ---------------------------------------------

                    if isinstance(
                        wake_result,
                        str
                    ):

                        command = (
                            wake_result
                        )

                    else:

                        command = None

                    # ---------------------------------------------
                    # Only "Vyom" was spoken.
                    # ---------------------------------------------

                    if not command:

                        response = (
                            "हाँ, बताइए।"
                        )

                        _safe_print(
                            "Vyom : "
                            + response
                        )

                        try:

                            self.speak(
                                response
                            )

                        except Exception:

                            pass

                        # -----------------------------------------
                        # Audio handoff delay.
                        # -----------------------------------------

                        time.sleep(
                            0.25
                        )

                        # -----------------------------------------
                        # Listen for first command.
                        # -----------------------------------------

                        command = (
                            self._listen_active_command()
                        )

                    # ---------------------------------------------
                    # No command after activation.
                    #
                    # Keep voice mode alive, but return to
                    # wake-word state.
                    # ---------------------------------------------

                    if not command:

                        self._deactivate()

                        continue

                    # ---------------------------------------------
                    # Execute command.
                    # ---------------------------------------------

                    self._execute_voice_command(
                        command
                    )

                    # ---------------------------------------------
                    # If exit was requested, leave loop.
                    # ---------------------------------------------

                    if not self.running:

                        break

                    # ---------------------------------------------
                    # Continuous conversation.
                    # ---------------------------------------------

                    if self.continuous_conversation:

                        self.activated = True

                        self.state = "listening"

                        _safe_print(
                            "Vyom : Listening..."
                        )

                        continue

                    # ---------------------------------------------
                    # Backward-safe fallback.
                    # ---------------------------------------------

                    self._deactivate()

                    time.sleep(
                        0.15
                    )

                    continue

                # =================================================
                # ACTIVE CONVERSATION
                #
                # Wake word is no longer required for every
                # command.
                # =================================================

                command = (
                    self._listen_active_command()
                )

                # -------------------------------------------------
                # Silence / recognition failure.
                #
                # Keep the same active conversation.
                # -------------------------------------------------

                if not command:

                    self.state = "listening"

                    continue

                # -------------------------------------------------
                # EXIT
                # -------------------------------------------------

                if self._is_exit_command(
                    command
                ):

                    self.running = False

                    response = (
                        "ठीक है, voice mode बंद कर रहा हूँ।"
                    )

                    _safe_print(
                        "Vyom : "
                        + response
                    )

                    try:

                        self.speak(
                            response
                        )

                    except Exception:

                        pass

                    break

                # -------------------------------------------------
                # EXECUTE COMMAND
                # -------------------------------------------------

                self._execute_voice_command(
                    command
                )

                # -------------------------------------------------
                # Continue listening.
                # -------------------------------------------------

                if self.running:

                    self.activated = True

                    self.state = "listening"

                    _safe_print(
                        "Vyom : Listening..."
                    )

                    time.sleep(
                        0.10
                    )

                continue

        except KeyboardInterrupt:

            self.running = False

            _safe_print("")

            _safe_print(
                "Vyom : Voice mode stopped."
            )

        except Exception as error:

            self.running = False

            _safe_print("")

            _safe_print(
                "Vyom : Voice controller error: "
                + str(error)
            )

        finally:

            self.running = False

            self.activated = False

            self.state = "idle"

            try:

                self.speech_to_text.stop_session()

            except Exception:

                pass

    # ========================================================
    # STOP
    # ========================================================

    def stop(self):

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


# ============================================================
# STANDALONE TEST
# ============================================================

def main():

    _safe_print(
        "=" * 60
    )

    _safe_print(
        "Vyom AI - Voice Controller Test"
    )

    _safe_print(
        "=" * 60
    )

    _safe_print("")

    controller = VoiceController()

    if not controller.is_available():

        _safe_print(
            "Voice input unavailable."
        )

        return

    controller.run()


if __name__ == "__main__":

    main()
