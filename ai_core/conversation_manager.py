"""
Project : Vyom AI
Version : 1.0
Module  : Conversation Manager

Purpose:
    Persistent conversational layer above the existing Executor.

Architecture:

    Text / Voice
          |
          v
    ConversationManager
          |
          v
    command_engine.executor.execute()
          |
          v
    Existing Vyom pipeline
          |
          +--> IntentEngine
          +--> AutonomousAgent
          +--> SessionMemory
          +--> ReasoningEngine
          +--> ToolManager
          +--> Observation / Verification
          +--> ResponseEngine

Important:
    - Existing Executor remains the actual integration point.
    - Existing ToolManager behaviour is not duplicated.
    - Existing AutonomousAgent is not replaced.
    - Conversation history is lightweight and in-memory.
    - This module does not execute arbitrary code.
"""

from typing import Any, Dict, List, Optional

from command_engine.executor import execute


class ConversationManager:

    def __init__(self, max_history: int = 20):
        self.max_history = max(1, int(max_history))
        self.history: List[Dict[str, Any]] = []
        self.active = True
        self.last_user_message = ""
        self.last_response = ""
        self.turn_count = 0

    # =========================================================
    # LANGUAGE
    # =========================================================

    @staticmethod
    def detect_language(text: Any) -> str:
        value = str(text or "").strip()

        if not value:
            return "unknown"

        has_hindi = any(
            "\u0900" <= char <= "\u097F"
            for char in value
        )

        has_latin = any(
            ("a" <= char.lower() <= "z")
            for char in value
        )

        if has_hindi and has_latin:
            return "hinglish"

        if has_hindi:
            return "hindi"

        if has_latin:
            return "english"

        return "unknown"

    # =========================================================
    # SESSION
    # =========================================================

    def reset(self) -> None:
        self.history = []
        self.active = True
        self.last_user_message = ""
        self.last_response = ""
        self.turn_count = 0

    def stop(self) -> None:
        self.active = False

    def start(self) -> None:
        self.active = True

    # =========================================================
    # HISTORY
    # =========================================================

    def _record(
        self,
        role: str,
        text: Any,
        result: Any = None
    ) -> None:

        item = {
            "turn": self.turn_count,
            "role": role,
            "text": str(text or ""),
            "language": self.detect_language(text),
        }

        if result is not None:
            item["result"] = result

        self.history.append(item)

        if len(self.history) > self.max_history:
            self.history = self.history[
                -self.max_history:
            ]

    # =========================================================
    # PROCESS ONE TURN
    # =========================================================

    def process(
        self,
        message: Any,
        source: str = "text"
    ) -> Dict[str, Any]:

        text = str(message or "").strip()

        if not text:
            return {
                "success": False,
                "stage": "empty_message",
                "message": "",
                "response": "",
                "source": source,
            }

        if not self.active:
            self.start()

        self.turn_count += 1
        self.last_user_message = text

        self._record(
            "user",
            text
        )

        # -----------------------------------------------------
        # Do NOT implement another command/intent engine here.
        #
        # Executor already owns:
        #   IntentEngine
        #   persistent AutonomousAgent
        #   SessionMemory
        #   ToolManager
        #   ResponseEngine
        #
        # Keeping one execution path prevents context divergence.
        # -----------------------------------------------------

        try:
            result = execute(text)

        except Exception as error:

            response = (
                "I could not process that request: "
                + str(error)
            )

            self.last_response = response

            self._record(
                "assistant",
                response,
                {
                    "success": False,
                    "error": str(error),
                }
            )

            return {
                "success": False,
                "stage": "conversation_error",
                "message": response,
                "response": response,
                "source": source,
                "language": self.detect_language(text),
                "turn": self.turn_count,
            }

        response = str(
            result
            if result is not None
            else ""
        ).strip()

        self.last_response = response

        self._record(
            "assistant",
            response,
            result
        )

        return {
            "success": True,
            "stage": "completed",
            "message": response,
            "response": response,
            "result": result,
            "source": source,
            "language": self.detect_language(text),
            "turn": self.turn_count,
            "history_size": len(self.history),
        }

    # =========================================================
    # TEXT ALIAS
    # =========================================================

    def process_text(
        self,
        text: Any
    ) -> Dict[str, Any]:

        return self.process(
            text,
            source="text"
        )

    # =========================================================
    # VOICE ALIAS
    # =========================================================

    def process_voice(
        self,
        text: Any
    ) -> Dict[str, Any]:

        return self.process(
            text,
            source="voice"
        )

    # =========================================================
    # HISTORY ACCESS
    # =========================================================

    def get_history(self) -> List[Dict[str, Any]]:
        return list(self.history)

    def get_recent_history(
        self,
        limit: int = 5
    ) -> List[Dict[str, Any]]:

        limit = max(1, int(limit))

        return list(
            self.history[-limit:]
        )

    def snapshot(self) -> Dict[str, Any]:

        return {
            "active": self.active,
            "turn_count": self.turn_count,
            "last_user_message": self.last_user_message,
            "last_response": self.last_response,
            "history": self.get_history(),
        }
