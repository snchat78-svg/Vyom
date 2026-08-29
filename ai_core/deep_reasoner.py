"""
Project : Vyom AI
Version : 0.1
Module  : Deep Reasoner

Purpose:
    Convert a natural-language goal into structured reasoning.

    This module does not execute actions.

Architecture:

    Goal
      ↓
    Session Context
      ↓
    Capabilities
      ↓
    ModelGateway
      ↓
    Structured Decision
"""

from typing import Any, Dict, Optional

from ai_core.model_gateway import ModelGateway


class DeepReasoner:

    def __init__(
        self,
        model_gateway: Optional[ModelGateway] = None
    ):

        self.model_gateway = (
            model_gateway
            if model_gateway is not None
            else ModelGateway()
        )

        self.last_result = None

    # =========================================================
    # REASON
    # =========================================================

    def reason(
        self,
        goal: str,
        context: Optional[Dict[str, Any]] = None,
        capabilities=None,
        previous_result=None
    ):

        result = self.model_gateway.complete(
            goal=goal,
            context=context,
            capabilities=capabilities,
            previous_result=previous_result
        )

        self.last_result = result

        if not isinstance(
            result,
            dict
        ):

            return {
                "success": False,
                "available": False,
                "error": (
                    "Invalid DeepReasoner result."
                )
            }

        return result

    # =========================================================
    # AVAILABLE
    # =========================================================

    def is_available(self):

        return self.model_gateway.is_available()

    # =========================================================
    # RESET
    # =========================================================

    def reset(self):

        self.last_result = None
