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

STEP 1:

    Voice mode uses VoiceController for:

        Wake Word
          ↓
        Continuous Conversation
          ↓
        Existing Executor
          ↓
        Persistent AutonomousAgent / SessionMemory
          ↓
        Response
          ↓
        Listen Again

    Main.py only starts/stops the voice controller.
    Continuous voice-session logic remains inside
    VoiceController.
"""

import os
import sys


def _safe_print(*args, **kwargs):
    """Never allow a Windows console failure to terminate Vyom."""
    try:
        print(*args, **kwargs)
    except (PermissionError, OSError):
        pass
    except Exception:
        pass


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
            stream.reconfigure(
                encoding="utf-8",
                errors="replace"
            )
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

_safe_print("===================================")
_safe_print(" Vyom AI Started ")
_safe_print("===================================")

_safe_print("")
_safe_print("Available modes:")
_safe_print("1. Text mode")
_safe_print("2. Voice mode")
_safe_print("")
_safe_print("Type a normal command to use text mode.")
_safe_print("Type 'voice' to start voice mode.")
_safe_print("Type 'exit' to close Vyom.")
_safe_print("")


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

        _safe_print("")
        _safe_print("Vyom : Goodbye")
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

        _safe_print("Vyom : Goodbye")
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

        _safe_print("")
        _safe_print("===================================")
        _safe_print(" Vyom AI - Voice Mode ")
        _safe_print("===================================")
        _safe_print("")

        if not voice_controller.is_available():

            _safe_print(
                "Vyom : Voice input is not available."
            )

            _safe_print(
                "Reason : "
                + str(
                    voice_controller.speech_to_text.error_message
                )
            )

            _safe_print("")

            continue


        _safe_print(
            "Vyom : Voice mode starting..."
        )

        # ----------------------------------------------------
        # STEP 1 - WAKE WORD
        #
        # VoiceController now waits for:
        #
        #     "Vyom"
        #
        # before entering active conversation.
        # ----------------------------------------------------

        _safe_print(
            "Vyom : Say 'Vyom' to activate me."
        )

        # ----------------------------------------------------
        # STEP 1 - CONTINUOUS CONVERSATION
        #
        # After activation, VoiceController keeps listening
        # after each completed command.
        #
        # Example:
        #
        #     Vyom
        #     Excel खोलो
        #     नई sheet बनाओ
        #     इसमें मेरा नाम लिखो
        #     इसे save करो
        #
        # The same persistent Executor /
        # AutonomousAgent / SessionMemory remains active.
        # ----------------------------------------------------

        _safe_print(
            "Vyom : After activation, keep speaking naturally."
        )

        # ----------------------------------------------------
        # EXIT
        #
        # VoiceController handles voice-session exit commands:
        #
        #     exit
        #     quit
        #     stop voice
        #     वॉइस बंद करो
        #
        # Main.py remains responsible for returning to text
        # mode after VoiceController stops.
        # ----------------------------------------------------

        _safe_print(
            "Vyom : Say 'exit' to close voice mode."
        )

        _safe_print("")


        try:

            voice_controller.run()

        except Exception as error:

            _safe_print(
                "Vyom : Voice mode error: "
                + str(error)
            )


        # ----------------------------------------------------
        # VoiceController has stopped.
        #
        # Return to the existing text-mode loop.
        # ----------------------------------------------------

        _safe_print("")
        _safe_print(
            "Vyom : Returned to text mode."
        )
        _safe_print("")

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

    _safe_print(
        "Vyom : "
        + str(response)
    )

    _safe_print("")
