"""
Project : Vyom AI
Version : 0.1
Module  : Brain
"""

from ai_core.logger import log

class Brain:

    def think(self, command):

        log(f"Received Command : {command}")

        return f"Command Accepted : {command}"
