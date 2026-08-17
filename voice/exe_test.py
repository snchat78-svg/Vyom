# ============================================================
# Project : Vyom AI
# Module  : exe_test.py
# Version : 0.1
#
# Purpose:
#     Standalone Voice Test for Vyom EXE
#
# Flow:
#     Microphone -> Speech To Text -> Display Text
#
# IMPORTANT:
#     This file does NOT modify existing Vyom command logic.
# ============================================================

import sys
import os

# ------------------------------------------------------------
# Make project root available
# ------------------------------------------------------------

PROJECT_ROOT = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

if PROJECT_ROOT not in sys.path:
    sys.path.insert(
        0,
        PROJECT_ROOT
    )


# ------------------------------------------------------------
# Import Speech To Text
# ------------------------------------------------------------

try:

    from voice.speech_to_text import SpeechToText

except Exception as error:

    print("")
    print("Vyom : Could not load SpeechToText.")
    print("Reason :", error)
    print("")

    input("Press Enter to exit...")
    sys.exit(1)


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 60)
    print(" Vyom AI - Voice EXE Test")
    print("=" * 60)
    print("")

    stt = SpeechToText()

    # --------------------------------------------------------
    # Check microphone / speech recognition
    # --------------------------------------------------------

    if not stt.is_available():

        print("STT Status : NOT AVAILABLE")
        print("")

        print(
            "Reason : "
            + stt.error_message
        )

        print("")
        input("Press Enter to exit...")

        return

    print("STT Status : READY")
    print("")

    print(
        "Microphone is ready."
    )

    print(
        "Speak after 'Listening...' appears."
    )

    print(
        "Say 'exit' to stop."
    )

    print("")

    # --------------------------------------------------------
    # Continuous voice test
    # --------------------------------------------------------

    while True:

        result = stt.listen(
            timeout=5,
            phrase_time_limit=8
        )

        if result.get("success"):

            text = result.get(
                "text",
                ""
            ).strip()

            print(
                "You : "
                + text
            )

            # ----------------------------------------------
            # EXIT
            # ----------------------------------------------

            if text.lower() in (
                "exit",
                "quit",
                "stop"
            ):

                print(
                    "Vyom : Voice test stopped."
                )

                break

        else:

            print(
                "Vyom : "
                + result.get(
                    "message",
                    "Speech recognition failed."
                )
            )

        print("")


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    main()
