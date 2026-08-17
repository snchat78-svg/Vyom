# ============================================================
# Project : Vyom AI
# Module  : voice_controller.py
# Version : 0.1
#
# Purpose:
#     Connect Speech-To-Text with Vyom's existing
#     Command Engine.
#
# Flow:
#
#     Microphone
#          ↓
#     SpeechToText
#          ↓
#     VoiceController
#          ↓
#     Command Engine Executor
#          ↓
#     IntentEngine
#          ↓
#     Brain
#          ↓
#     ToolManager
#
# IMPORTANT:
#     Existing ToolManager / IntentEngine code is NOT changed.
# ============================================================


from voice.speech_to_text import SpeechToText

from command_engine.executor import execute


class VoiceController:

    # ========================================================
    # INITIALIZATION
    # ========================================================

    def __init__(self):

        self.speech_to_text = SpeechToText()

        self.running = False

    # ========================================================
    # STATUS
    # ========================================================

    def is_available(self):

        return self.speech_to_text.is_available()

    # ========================================================
    # PROCESS TEXT COMMAND
    #
    # This method is important because it allows us to test
    # the voice pipeline without microphone hardware.
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
                )
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
                )
            }

        # ----------------------------------------------------
        # Send command to existing Vyom command engine.
        #
        # DO NOT duplicate IntentEngine logic here.
        # Executor already handles:
        #
        #     IntentEngine
        #     Brain
        #     ToolManager
        # ----------------------------------------------------

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

    def listen_once(self):

        if not self.is_available():

            return {
                "success": False,
                "text": "",
                "message": (
                    "Speech recognition is not available: "
                    + self.speech_to_text.error_message
                )
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
                )
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
                )
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
        print("Vyom AI - Voice Command Mode")
        print("=" * 60)
        print("")
        print(
            "Speak a command."
        )
        print(
            "Say 'exit' or 'quit' to stop."
        )
        print("")

        while self.running:

            try:

                result = self.listen_once()

                if not result.get(
                    "success",
                    False
                ):

                    print(
                        "Vyom : "
                        + result.get(
                            "message",
                            "Voice command failed."
                        )
                    )

                    print("")

                    continue

                text = result.get(
                    "text",
                    ""
                ).strip()

                print(
                    "You : "
                    + text
                )

                # ------------------------------------------------
                # Voice loop exit commands
                # ------------------------------------------------

                if text.lower() in (
                    "exit",
                    "quit"
                ):

                    self.running = False

                    print(
                        "Vyom : Voice mode stopped."
                    )

                    break

                print(
                    "Vyom : "
                    + result.get(
                        "message",
                        ""
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


# ============================================================
# STANDALONE TEXT TEST
#
# This test does NOT require a microphone.
#
# It verifies:
#
#     VoiceController
#          ↓
#     Executor
#          ↓
#     IntentEngine
#          ↓
#     Brain
#          ↓
#     ToolManager
#
# ============================================================

def main():

    print("=" * 60)
    print("Vyom AI - Voice Controller Test")
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

        print(
            "Vyom : "
            + result.get(
                "message",
                ""
            )
        )

        print("")


if __name__ == "__main__":

    main()
