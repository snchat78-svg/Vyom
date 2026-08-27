# ============================================================
# Project : Vyom AI
# Module  : voice_controller.py
# Version : 0.2
#
# Purpose:
#     Connect Speech-To-Text + Command Engine + Text-To-Speech
#
# Flow:
#
#     Microphone
#          ↓
#     SpeechToText
#          ↓
#     VoiceController
#          ↓
#     Command Executor
#          ↓
#     AutonomousAgent
#          ↓
#     ReasoningEngine
#          ↓
#     ToolManager
#          ↓
#     Windows / Files / Applications
#          ↓
#     TextToSpeech
#          ↓
#     Speaker
#
# IMPORTANT:
#
#     Existing IntentEngine / ToolManager behaviour is preserved.
# ============================================================


from voice.speech_to_text import SpeechToText
from voice.text_to_speech import TextToSpeech

from command_engine.executor import execute


def _safe_print(*args, **kwargs):
    """Never allow a broken Windows console to terminate Vyom."""
    try:
        print(*args, **kwargs)
    except (PermissionError, OSError):
        pass
    except Exception:
        pass


class VoiceController:

    # ========================================================
    # INITIALIZATION
    # ========================================================

    def __init__(self):

        self.speech_to_text = SpeechToText()

        self.text_to_speech = TextToSpeech()

        self.running = False

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
        # Existing command pipeline
        #
        # DO NOT duplicate IntentEngine logic here.
        #
        # Executor already handles:
        #
        #     IntentEngine
        #     Brain
        #     AutonomousAgent
        #     ReasoningEngine
        #     ToolManager
        # ----------------------------------------------------

        try:

            result = execute(
                text
            )

            message = str(
                result
            )

            return {
                "success": True,
                "text": text,
                "message": message,
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
        announce=False
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

        speech_result = self.speech_to_text.listen(
            announce=announce
        )

        # ----------------------------------------------------
        # Silence is normal.
        #
        # Do not speak an error and do not create a new task.
        # ----------------------------------------------------

        if speech_result.get("status") == "silence":

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
                    "Speech recognition failed."
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

        return self.process_text(
            text
        )

    # ========================================================
    # RUN VOICE LOOP
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

        _safe_print("")
        _safe_print("=" * 60)
        _safe_print("Vyom AI - Voice Command Mode")
        _safe_print("=" * 60)
        _safe_print("")
        _safe_print(
            "Vyom : I'm ready. Tell me what you want to do."
        )
        _safe_print(
            "Vyom : You can speak naturally. Say 'exit' or 'quit' to stop."
        )
        _safe_print("")

        # Open one microphone/PyAudio stream for the whole voice session.
        # This is the key stability change for older Windows systems.
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

        first_listen = True

        try:

            while self.running:

                try:

                    result = self.listen_once(
                        announce=first_listen
                    )

                    first_listen = False

                    # Silence is normal. Keep waiting quietly.
                    if result.get("status") == "silence":
                        continue

                    if not result.get("success", False):

                        status = result.get("status", "error")
                        message = result.get("message", "")

                        # Unrecognized speech and silence are deliberately
                        # silent states. Device errors are recoverable and
                        # are handled by SpeechToText.
                        if status in (
                            "unrecognized",
                            "silence"
                        ):
                            continue

                        if message:
                            _safe_print(
                                "Vyom : " + message
                            )
                            _safe_print("")

                        continue

                    text = result.get("text", "").strip()

                    if not text:
                        continue

                    _safe_print(
                        "You : " + text
                    )

                    text_lower = text.lower().strip()

                    if text_lower in (
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
                            if any(
                                token in text_lower
                                for token in ("बंद", "करो")
                            )
                            else "Okay, voice mode stopped."
                        )

                        _safe_print(
                            "Vyom : " + response
                        )
                        self.speak(response)
                        break

                    response = result.get(
                        "message",
                        ""
                    )

                    if not response:
                        continue

                    _safe_print(
                        "Vyom : " + response
                    )
                    _safe_print("")

                    # Give the Windows audio driver a small handoff period
                    # after TTS before the next microphone capture.
                    tts_result = self.speak(response)

                    if not tts_result.get("success", False):
                        _safe_print(
                            "Vyom TTS : "
                            + tts_result.get(
                                "message",
                                "Speech output failed."
                            )
                        )

                    import time
                    time.sleep(0.20)

                except KeyboardInterrupt:

                    self.running = False
                    _safe_print("")
                    _safe_print("Vyom : Voice mode stopped.")
                    break

                except PermissionError as error:

                    # Do not let WinError 31 escape through the console or
                    # terminate the EXE. Reinitialize the microphone once.
                    _safe_print(
                        "Vyom : Microphone connection was interrupted. Recovering..."
                    )

                    try:
                        self.speech_to_text.stop_session()
                    except Exception:
                        pass

                    import time
                    time.sleep(0.50)

                    if not self.speech_to_text.start_session():
                        _safe_print(
                            "Vyom : Microphone could not be recovered yet. Waiting..."
                        )
                        time.sleep(1.0)

                except OSError as error:

                    _safe_print(
                        "Vyom : Audio device temporarily failed. Recovering..."
                    )

                    try:
                        self.speech_to_text.stop_session()
                    except Exception:
                        pass

                    import time
                    time.sleep(0.50)

                    self.speech_to_text.start_session()

                except Exception as error:

                    # Any unexpected command/voice error is contained inside
                    # the session. The next user instruction can continue.
                    _safe_print(
                        "Vyom : Voice command error recovered: "
                        + str(error)
                    )
                    import time
                    time.sleep(0.25)

        finally:

            self.running = False

            try:
                self.speech_to_text.stop_session()
            except Exception:
                pass

    # ========================================================
    # STOP
    # ========================================================

    def stop(self):

        self.running = False

        try:

            self.text_to_speech.stop()

        except Exception:

            pass


# ============================================================
# STANDALONE TEXT TEST
# ============================================================

def main():

    _safe_print("=" * 60)

    _safe_print(
        "Vyom AI - Voice Controller Test"
    )

    _safe_print("=" * 60)

    _safe_print("")

    controller = VoiceController()

    _safe_print(
        "Text integration test."
    )

    _safe_print(
        "Type commands instead of speaking."
    )

    _safe_print(
        "Type 'exit' to stop."
    )

    _safe_print("")

    while True:

        try:

            command = input(
                "You : "
            ).strip()

        except (
            KeyboardInterrupt,
            EOFError
        ):

            _safe_print("")

            break

        if not command:

            continue

        if command.lower() in (
            "exit",
            "quit"
        ):

            _safe_print(
                "Vyom : Test stopped."
            )

            break

        result = controller.process_text(
            command
        )

        message = result.get(
            "message",
            ""
        )

        _safe_print(
            "Vyom : "
            + message
        )

        # TTS test

        controller.speak(
            message
        )

        _safe_print("")


if __name__ == "__main__":

    main()
