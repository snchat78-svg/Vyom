# ============================================================
# Project : Vyom AI
# Module  : exe_test.py
# Version : 0.1
#
# Purpose:
#     Standalone EXE test entry point for Vyom Voice.
#
# IMPORTANT:
#     This file does not replace main.py.
#     It is only used for Windows EXE testing.
# ============================================================

from voice.voice_controller import VoiceController


def main():

    print("=" * 60)
    print("Vyom AI - EXE Test")
    print("=" * 60)
    print("")

    controller = VoiceController()

    # --------------------------------------------------------
    # Check Speech Recognition
    # --------------------------------------------------------

    if not controller.is_available():

        print(
            "Vyom : Speech recognition is not available."
        )

        print(
            "Reason : "
            + str(
                controller.stt.error_message
            )
        )

        input(
            "\nPress Enter to exit..."
        )

        return

    print(
        "Vyom : Voice system is ready."
    )

    print("")
    print(
        "Speak a command."
    )
    print(
        "Say 'exit' or 'quit' to stop."
    )
    print("")

    # --------------------------------------------------------
    # Voice loop
    # --------------------------------------------------------

    try:

        while True:

            response = (
                controller.listen_and_execute()
            )

            print("")

            print(
                "Vyom : "
                + str(
                    response.get(
                        "message",
                        ""
                    )
                )
            )

            print("")

    except KeyboardInterrupt:

        print("")
        print(
            "Vyom : Voice test stopped."
        )

    except Exception as error:

        print("")
        print(
            "Vyom : Unexpected error:"
        )

        print(
            str(error)
        )

    finally:

        input(
            "\nPress Enter to exit..."
        )


if __name__ == "__main__":

    main()
