"""
Project : Vyom AI
Version : 0.4
Module  : Executor
"""

from ai_core.brain import Brain
from command_engine.intent import IntentEngine
from windows_agent.launcher import WindowsLauncher

brain = Brain()
intent_engine = IntentEngine()
launcher = WindowsLauncher()


def execute(command):

    intent = intent_engine.detect(command)

    # Brain logs and understands the command
    brain.think(intent)

    if intent["intent"] == "open_app":
        return launcher.open_app(intent["target"])

    return f"Unsupported intent: {intent['intent']}"
