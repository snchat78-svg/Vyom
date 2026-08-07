"""
Project : Vyom AI
Version : 0.2
Module  : Executor
"""

from ai_core.brain import Brain
from command_engine.intent import IntentEngine

brain = Brain()
intent_engine = IntentEngine()

def execute(command):

    intent = intent_engine.detect(command)

    return brain.think(intent)
