# ============================================================
# Project : Vyom AI
# Module  : voice_command.py
# Version : 0.1
#
# Purpose:
#     Connect Vyom Speech-to-Text with Command Engine.
#
# Flow:
#
#     Microphone
#         ↓
#     SpeechToText
#         ↓
#     Text Command
#         ↓
#     Command Engine Executor
#         ↓
#     Intent Engine
#         ↓
#     Tool Manager
#         ↓
#     Windows Action
#
# Designed for:
#     Windows 8.1 / Windows 10 / Windows 11
#
# IMPORTANT:
#     Existing modules are not replaced.
# ============================================================


from voice.speech_to_text import SpeechToText
from command_engine.executor import execute


class VoiceCommandController:

    # ========================================================
    # INITIALIZATION
    # ========================================================

    def __init__(self):

        self.stt = SpeechToText()

    # ========================================================
    # STATUS
    # ========================================================

    def is_available(self):

        return self.stt.is_available()

    # ========================================================
    # LISTEN AND EXECUTE ONE COMMAND
    # ========================================================

    def listen_and_execute(
        self,
        timeout=5,
        phrase_time_limit=8
    ):

        # ----------------------------------------------------
        # Check Speech-to-Text
        # ----------------------------------------------------

        if not self.stt.is_available():

            return {
                "success": False,
                "text": "",
                "message": (
                    "Speech recognition is not available: "
                    + self.stt.error_message
                ),
                "result": None
            }

        # ----------------------------------------------------
        # Listen
        # ----------------------------------------------------

        speech_result = self.stt.listen(
            timeout=timeout,
            phrase_time_limit=phrase_time_limit
        )

        # ----------------------------------------------------
        # Speech recognition failed
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # Get recognized text
        # ----------------------------------------------------

        command = str(
            speech_result.get(
                "text",
                ""
            )
        ).strip()

        if not command:

            return {
                "success": False,
                "text": "",
                "message": (
                    "No command was recognized."
                ),
                "result": None
            }

        # ----------------------------------------------------
        # Display recognized command
        # ----------------------------------------------------

        print(
            "You : "
            + command
        )

        # ----------------------------------------------------
        # SEND TEXT TO EXISTING COMMAND ENGINE
        #
        # executor.execute() already performs:
        #
        # Command
        #   ↓
        # IntentEngine
        #   ↓
        # Brain
        #   ↓
        # ToolManager
        #
        # Existing command flow remains unchanged.
        # ----------------------------------------------------

        try:

            result = execute(
                command
            )

        except Exception as error:

            return {
                "success": False,
                "text": command,
                "message": (
                    "Command execution failed: "
                    + str(error)
                ),
                "result": None
            }

        # ----------------------------------------------------
        # Convert result to readable message
        # ----------------------------------------------------

        if isinstance(
            result,
            dict
        ):

            message = str(
                result.get(
                    "message",
                    result
                )
            )

        else:

            message = str(
                result
            )

        return {
            "success": True,
            "text": command,
            "message": message,
            "result": result
        }


# ============================================================
# STANDALONE TEST
#
# This test connects:
#
#     Microphone
#          ↓
#     Speech-to-Text
#          ↓
#     Command Engine
#          ↓
#     Existing Vyom Tools
#
# Examples:
#
#     "open calculator"
#     "open chrome"
#     "search 10th"
#     "close chrome"
#
# ============================================================

def main():

    print("=" * 60)
    print("Vyom AI - Voice Command Controller")
    print("=" * 60)
    print("")
    print(
        "Voice -> Text -> Command Engine -> Tool"
    )
    print("")
    print(
        "Press Ctrl+C to stop."
    )
    print("")

    controller = VoiceCommandController()

    # --------------------------------------------------------
    # Check STT
    # --------------------------------------------------------

    if not controller.is_available():

        print(
            "Vyom : Speech recognition is not available."
        )

        print(
            "Reason : "
            + controller.stt.error_message
        )

        return

    print(
        "Vyom : Voice command system is ready."
    )

    print("")

    # --------------------------------------------------------
    # Continuous voice command loop
    # --------------------------------------------------------

    try:

        while True:

            response = (
                controller.listen_and_execute()
            )

            print("")

            print(
                "Vyom : "
                + response.get(
                    "message",
                    ""
                )
            )

            print("")

    except KeyboardInterrupt:

        print("")

        print(
            "Vyom : Voice command system stopped."
        )


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":

    main()
