"""
Project : Vyom AI
Version : 0.2
Module  : Brain
"""

from ai_core.logger import log

class Brain:

    def think(self, data):

        log(f"Intent : {data['intent']}")
        log(f"Target : {data['target']}")

        return f"Intent = {data['intent']} | Target = {data['target']}"
