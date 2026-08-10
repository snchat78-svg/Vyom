"""
Project : Vyom AI
Version : 0.8
Module : Executor
"""

from ai_core.brain import Brain
from command_engine.intent import IntentEngine
from tools.tool_manager import ToolManager


brain = Brain()
intent_engine = IntentEngine()
tool_manager = ToolManager()


def execute(command):

    intent = intent_engine.detect(command)

    brain.think(intent)

    return tool_manager.execute(intent)
