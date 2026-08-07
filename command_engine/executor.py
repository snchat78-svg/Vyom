"""
Project : Vyom AI
Version : 0.5
Module  : Executor
"""

from ai_core.brain import Brain
from command_engine.intent import IntentEngine
from windows_agent.launcher import WindowsLauncher
from windows_agent.process_manager import ProcessManager

brain = Brain()
intent_engine = IntentEngine()
launcher = WindowsLauncher()
process_manager = ProcessManager()


def execute(command):

    intent = intent_engine.detect(command)

    brain.think(intent)

    if intent["intent"] == "open_app":
        return launcher.open_app(intent["target"])

    elif intent["intent"] == "close_app":
        return process_manager.close_app(intent["target"])

    return f"Unknown command : {intent['target']}"
