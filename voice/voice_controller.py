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
            "Vyom : I'm ready. Tell me what you want to do."
        )
        print(
            "Vyom : You can speak naturally. Say 'exit' or 'quit' to stop."
        )
        print("")

        # ----------------------------------------------------
        # IMPORTANT:
        #
        # Listening is continuous, but silence is silent.
        # Vyom does not repeatedly announce "Listening..."
        # and does not treat silence as an error.
        # ----------------------------------------------------

        first_listen = True

        while self.running:

            try:

                result = self.listen_once(
                    announce=first_listen
                )

                first_listen = False

                # ------------------------------------------------
                # Silence
                # ------------------------------------------------

                if result.get("status") == "silence":

                    continue

                # ------------------------------------------------
                # Speech recognition error
                #
                # Only real recognition/service errors are shown.
                # ------------------------------------------------

                if not result.get(
                    "success",
                    False
                ):

                    status = result.get(
                        "status",
                        "error"
                    )

                    # No transcript is a recoverable voice state.
                    # Do not make the assistant repeatedly say
                    # "I could not understand...". Simply wait for
                    # the next real utterance.
                    if status in (
                        "unrecognized",
                        "silence"
                    ):
                        continue

                    message = result.get(
                        "message",
                        ""
                    )

                    if message:

                        print(
                            "Vyom : "
                            + message
                        )

                        print("")

                        # Service errors are real system errors, not
                        # normal speech failures, so report them once.
                        if status == "service_error":
                            self.speak(message)

                    continue

                # ------------------------------------------------
                # Recognized text
                # ------------------------------------------------

                text = result.get(
                    "text",
                    ""
                ).strip()

                if not text:

                    continue

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
                    "stop voice mode",
                    "बंद करो",
                    "वॉइस बंद करो",
                    "वॉयस बंद करो"
                ):

                    self.running = False

                    response = (
                        "ठीक है, voice mode बंद कर रहा हूँ।"
                        if any(
                            token in text.lower()
                            for token in (
                                "बंद",
                                "करो"
                            )
                        )
                        else "Okay, voice mode stopped."
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

                if not response:

                    continue

                print(
                    "Vyom : "
                    + response
                )

                print("")

                # ------------------------------------------------
                # SPEAK NATURAL RESPONSE
                # ------------------------------------------------

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

                # Keep the voice session alive after a recoverable
                # controller error instead of terminating the agent.
                continue

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
