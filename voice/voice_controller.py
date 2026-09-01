# ============================================================
# Project : Vyom AI
# Module  : voice_controller.py
# Version : 0.3
#
# Purpose:
#     Controlled voice interface for Vyom AI.
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
#     IDLE
#
# IMPORTANT:
#
#     Existing Executor / AutonomousAgent / ToolManager
#     integration is preserved.
#
#     This module does NOT duplicate IntentEngine logic.
# ============================================================

import time

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
        # Activation mode
        #
        # False:
        #     Vyom waits for wake word.
        #
        # True:
        #     Vyom is currently accepting one command.
        # ----------------------------------------------------

        self.activated = False

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
    # WAKE WORD CHECK
    # ========================================================

    def _is_wake_word(
        self,
        text
    ):

        value = str(
            text or ""
        ).strip().lower()

        if not value:

            return False

        for wake_word in self.wake_words:

            if value == wake_word:

                return True

        return False

    # ========================================================
    # REMOVE WAKE WORD FROM COMMAND
    # ========================================================

    def _remove_wake_word(
        self,
        text
    ):

        value = str(
            text or ""
        ).strip()

        lower_value = value.lower()

        for wake_word in self.wake_words:

            if lower_value == wake_word:

                return ""

            if lower_value.startswith(
                wake_word + " "
            ):

                return value[
                    len(wake_word):
                ].strip()

        return value

    # ========================================================
    # ACTIVATE
    # ========================================================

    def _activate(self):

        self.activated = True

        self.state = "listening"

        _safe_print(
            "Vyom : Listening for your command..."
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

            return False

        text = result.get(
            "text",
            ""
        ).strip()

        if not text:

            return False

        # ----------------------------------------------------
        # Wake word + command in same sentence
        #
        # Example:
        #
        #     "Vyom open notepad"
        # ----------------------------------------------------

        command = self._remove_wake_word(
            text
        )

        if command != text:

            self._activate()

            if command:

                return command

            return True

        return False

    # ========================================================
    # LISTEN FOR ONE ACTIVE COMMAND
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
        _safe_print("=" * 60)
        _safe_print(
            "Vyom AI - Voice Assistant"
        )
        _safe_print("=" * 60)
        _safe_print("")
        _safe_print(
            "Vyom : Say 'Vyom' when you want me."
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
                # IDLE
                #
                # ONLY wake-word detection happens here.
                # No command execution.
                # =================================================

                if not self.activated:

                    wake_result = (
                        self._wait_for_activation()
                    )

                    # ---------------------------------------------
                    # Wake word detected
                    # ---------------------------------------------

                    if wake_result:

                        # Wake word + command
                        if isinstance(
                            wake_result,
                            str
                        ):

                            command = wake_result

                            self.activated = True

                        else:

                            command = None

                        # -----------------------------------------
                        # If only "Vyom" was spoken
                        # -----------------------------------------

                        if not command:

                            response = (
                                "हाँ, बताइए।"
                            )

                            _safe_print(
                                "Vyom : "
                                + response
                            )

                            self.speak(
                                response
                            )

                            # Wait for exactly one command.
                            command = (
                                self._listen_active_command()
                            )

                        # -----------------------------------------
                        # No command after activation
                        # -----------------------------------------

                        if not command:

                            self._deactivate()

                            continue

                        # -----------------------------------------
                        # STOP COMMAND
                        # -----------------------------------------

                        command_lower = (
                            command.lower().strip()
                        )

                        if command_lower in (
                            "exit",
                            "quit",
                            "stop voice",
                            "stop voice mode",
                            "बंद करो",
                            "वॉइस बंद करो",
                            "वॉयस बंद करो"
                        ):

                            self.running = False

                            response = (
                                "ठीक है, voice mode बंद कर रहा हूँ।"
                            )

                            _safe_print(
                                "Vyom : "
                                + response
                            )

                            self.speak(
                                response
                            )

                            break

                        # =================================================
                        # PROCESS COMMAND
                        # =================================================

                        self.state = "processing"

                        _safe_print(
                            "Vyom : Processing command..."
                        )

                        result = self.process_text(
                            command
                        )

                        # =================================================
                        # SPEAK RESULT
                        # =================================================

                        response = result.get(
                            "message",
                            ""
                        )

                        if response:

                            self.state = "speaking"

                            _safe_print(
                                "Vyom : "
                                + response
                            )

                            self.speak(
                                response
                            )

                        # =================================================
                        # IMPORTANT:
                        #
                        # After ONE command:
                        #
                        #     active → idle
                        #
                        # Vyom will NOT immediately process another
                        # microphone input.
                        # =================================================

                        self._deactivate()

                        time.sleep(
                            0.15
                        )

                        continue

                else:

                    # ------------------------------------------------
                    # Safety fallback
                    # ------------------------------------------------

                    self._deactivate()

        except KeyboardInterrupt:

            self.running = False

            _safe_print(
                ""
            )

            _safe_print(
                "Vyom : Voice mode stopped."
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
