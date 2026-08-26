"""
Project : Vyom AI
Version : 0.2
Module  : Main

Purpose:
    Main entry point for Vyom AI.

Current flow:

    TEXT:
        User
          ↓
        CommandParser
          ↓
        Command Executor
          ↓
        AutonomousAgent
          ↓
        ReasoningEngine
          ↓
        ToolManager
          ↓
        Windows / Files / Applications

    VOICE:
        Microphone
          ↓
        SpeechToText
          ↓
        VoiceController
          ↓
        Command Executor
          ↓
        AutonomousAgent
          ↓
        ReasoningEngine
          ↓
        ToolManager
          ↓
        Windows / Files / Applications

IMPORTANT:

    Existing text command behaviour is preserved.

    VoiceController already uses the existing Executor,
    therefore voice commands use the same AI pipeline as
    normal text commands.

    No duplicate IntentEngine or ToolManager logic is
    created here.
"""

import os
import sys


def _configure_console():
    """Keep Hindi/Unicode text intact in the Windows console when possible."""

    if os.name != "nt":
        return

    try:
        os.system("chcp 65001 >nul")
    except Exception:
        pass

    for stream in (sys.stdin, sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


_configure_console()

from command_engine.parser import CommandParser
from command_engine.executor import execute

from voice.voice_controller import VoiceController


# ============================================================
# CORE COMPONENTS
# ============================================================

parser = CommandParser()

voice_controller = VoiceController()


# ============================================================
# STARTUP
# ============================================================

print("===================================")
print(" Vyom AI Started ")
print("===================================")

print("")
print("Available modes:")
print("1. Text mode")
print("2. Voice mode")
print("")
print("Type a normal command to use text mode.")
print("Type 'voice' to start voice mode.")
print("Type 'exit' to close Vyom.")
print("")


# ============================================================
# MAIN LOOP
# ============================================================

while True:

    try:

        command = input("You : ").strip()

    except (
        KeyboardInterrupt,
        EOFError
    ):

        print("")
        print("Vyom : Goodbye")
        break


    # ========================================================
    # EMPTY COMMAND
    # ========================================================

    if not command:

        continue


    command_lower = command.lower().strip()


    # ========================================================
    # EXIT
    # ========================================================

    if command_lower in (
        "exit",
        "quit",
        "close vyom"
    ):

        print("Vyom : Goodbye")
        break


    # ========================================================
    # VOICE MODE
    # ========================================================

    if command_lower in (
        "voice",
        "voice mode",
        "start voice",
        "start voice mode",
        "listen"
    ):

        print("")
        print("===================================")
        print(" Vyom AI - Voice Mode ")
        print("===================================")
        print("")

        if not voice_controller.is_available():

            print(
                "Vyom : Voice input is not available."
            )

            print(
                "Reason : "
                + str(
                    voice_controller.speech_to_text.error_message
                )
            )

            print("")

            continue


        print(
            "Vyom : Voice mode starting..."
        )

        print(
            "Vyom : Speak your command."
        )

        print(
            "Vyom : Say 'exit' or 'quit' to stop voice mode."
        )

        print("")


        try:

            voice_controller.run()

        except Exception as error:

            print(
                "Vyom : Voice mode error: "
                + str(error)
            )


        print("")
        print(
            "Vyom : Returned to text mode."
        )
        print("")

        continue


    # ========================================================
    # NORMAL TEXT COMMAND
    # ========================================================

    try:

        parsed = parser.parse(
            command
        )

        response = execute(
            parsed
        )

    except Exception as error:

        response = (
            "Vyom execution error: "
            + str(error)
        )


    # ========================================================
    # RESPONSE
    # ========================================================

    print(
        "Vyom : "
        + str(response)
    )

    print("")
