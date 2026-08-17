# ============================================================
# Project : Vyom AI
# Module  : test_speech_to_text.py
# Version : 0.1
#
# Purpose:
#     Standalone test for Vyom Speech-to-Text module.
#
# IMPORTANT:
#     This test does NOT modify:
#         - Parser
#         - Brain
#         - Intent Engine
#         - Tool Manager
#         - File Manager
#         - Process Manager
#
#     It only tests the Voice/STT layer.
# ============================================================

from speech_to_text import SpeechToText


def main():

    print("=" * 60)
    print("Vyom AI - Speech To Text Test")
    print("=" * 60)
    print("")

    stt = SpeechToText()

    # --------------------------------------------------------
    # CHECK STT AVAILABILITY
    # --------------------------------------------------------

    if not stt.is_available():

        print("STT : NOT AVAILABLE")
        print("")
        print(
            "Reason:"
        )
        print(
            stt.error_message
        )
        print("")
        print(
            "Voice module test stopped."
        )

        return

    print(
        "STT : READY"
    )

    print("")
    print(
        "Say a short sentence."
    )
    print(
        "Example: open calculator"
    )
    print("")
    print(
        "Press Ctrl+C to stop."
    )
    print("")

    # --------------------------------------------------------
    # LISTEN LOOP
    # --------------------------------------------------------

    while True:

        try:

            result = stt.listen(
                timeout=5,
                phrase_time_limit=8
            )

            if result.get("success"):

                text = result.get(
                    "text",
                    ""
                )

                print(
                    "You : "
                    + text
                )

            else:

                print(
                    "Vyom : "
                    + result.get(
                        "message",
                        "Speech recognition failed."
                    )
                )

            print("")

        except KeyboardInterrupt:

            print("")
            print(
                "Vyom : Voice test stopped."
            )

            break

        except Exception as error:

            print(
                "Vyom : Unexpected error:"
            )

            print(
                str(error)
            )

            print("")


if __name__ == "__main__":

    main()
