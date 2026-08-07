"""
Project : Vyom AI
Version : 0.1
Module  : Executor
"""

from ai_core.brain import Brain

brain = Brain()

def execute(command):

    return brain.think(command)
