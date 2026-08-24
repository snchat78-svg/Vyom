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

    def listen_once(self):

        if not self.is_available():

            return {
                "success": False,
                "text": "",
                "message": (
                    "Speech recognition is not available: "
                    + self.speech_to_text.error_message
                ),
                "result": None
            }

        speech_result = self.speech_to_text.listen()

        if not speech_result.get(
            "success",
            False
        ):

            return {
                "success": False,
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
                "text": "",
                "message": (
                    "No speech command was detected."
                ),
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

            print(
                "Vyom : Voice input is not available."
            )

            print(
                "Reason : "
                + self.speech_to_text.error_message
            )

            return

        self.running = True

        print("")

        print("=" * 60)

        print(
            "Vyom AI - Voice Command Mode"
        )

        print("=" * 60)

        print("")

        print(
            "Speak a command."
        )

        print(
            "Vyom will execute the command "
            "and speak the response."
        )

        print(
            "Say 'exit' or 'quit' to stop."
        )

        print("")

        # ====================================================
        # CONTINUOUS VOICE LOOP
        # ====================================================

        while self.running:

            try:

                result = self.listen_once()

                # ------------------------------------------------
                # Failed speech
                # ------------------------------------------------

                if not result.get(
                    "success",
                    False
                ):

                    message = result.get(
                        "message",
                        "Voice command failed."
                    )

                    print(
                        "Vyom : "
                        + message
                    )

                    print("")

                    continue

                # ------------------------------------------------
                # Recognized text
                # ------------------------------------------------

                text = result.get(
                    "text",
                    ""
                ).strip()

                print(
                    "You : "
                    + text
                )

                # ------------------------------------------------
                # Voice loop exit
                # ------------------------------------------------

                if text.lower() in (
                    "exit",
                    "quit",
                    "stop voice",
                    "stop voice mode"
                ):

                    self.running = False

                    response = (
                        "Voice mode stopped."
                    )

                    print(
                        "Vyom : "
                        + response
                    )

                    self.speak(
                        response
                    )

                    break

                # ------------------------------------------------
                # Command result
                # ------------------------------------------------

                response = result.get(
                    "message",
                    ""
                )

                print(
                    "Vyom : "
                    + response
                )

                print("")

                # ------------------------------------------------
                # SPEAK RESULT
                # ------------------------------------------------

                if response:

                    tts_result = self.speak(
                        response
                    )

                    if not tts_result.get(
                        "success",
                        False
                    ):

                        print(
                            "Vyom TTS : "
                            + tts_result.get(
                                "message",
                                "Speech output failed."
                            )
                        )

                    print("")

            except KeyboardInterrupt:

                self.running = False

                print("")

                print(
                    "Vyom : Voice mode stopped."
                )

                break

            except Exception as error:

                print(
                    "Vyom : Voice controller error: "
                    + str(error)
                )

                print("")

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

    print("=" * 60)

    print(
        "Vyom AI - Voice Controller Test"
    )

    print("=" * 60)

    print("")

    controller = VoiceController()

    print(
        "Text integration test."
    )

    print(
        "Type commands instead of speaking."
    )

    print(
        "Type 'exit' to stop."
    )

    print("")

    while True:

        try:

            command = input(
                "You : "
            ).strip()

        except (
            KeyboardInterrupt,
            EOFError
        ):

            print("")

            break

        if not command:

            continue

        if command.lower() in (
            "exit",
            "quit"
        ):

            print(
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

        print(
            "Vyom : "
            + message
        )

        # TTS test

        controller.speak(
            message
        )

        print("")


if __name__ == "__main__":

    main()
