"""Lightweight voice/text façade over Vyom's existing executor.

Conversation history is bounded presentation history only.  The persistent
execution context continues to live in executor -> AutonomousAgent ->
SessionMemory.
"""

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import time
from typing import Any, Callable, Dict, List, Optional

from ai_core.conversation_result import ConversationResult, ConversationStatus
from command_engine.executor import execute


@dataclass
class ConversationTurn:
    timestamp: str
    source: str
    input_text: str
    language: str
    response_text: str
    status: str
    error_category: Optional[str] = None
    duration_ms: Optional[int] = None


class ConversationManager:
    """Routes one text or voice turn through the existing executor."""

    def __init__(
        self,
        max_history: int = 20,
        executor: Optional[Callable[[str], Any]] = None,
    ):
        self.max_history = max(1, int(max_history))
        self.history: List[ConversationTurn] = []
        self._executor = executor or execute
        self.active = True
        self.last_user_message = ""
        self.last_response = ""
        self.turn_count = 0

    @staticmethod
    def detect_language(text: Any) -> str:
        value = str(text or "").strip()
        if not value:
            return "unknown"
        has_hindi = any("\u0900" <= char <= "\u097F" for char in value)
        has_latin = any("a" <= char.lower() <= "z" for char in value)
        if has_hindi and has_latin:
            return "hinglish"
        if has_hindi:
            return "hindi"
        if has_latin:
            return "english"
        return "unknown"

    def reset(self) -> None:
        self.history.clear()
        self.active = True
        self.last_user_message = ""
        self.last_response = ""
        self.turn_count = 0

    def stop(self) -> None:
        self.active = False

    def start(self) -> None:
        self.active = True

    def _append_turn(self, turn: ConversationTurn) -> None:
        self.history.append(turn)
        del self.history[:-self.max_history]

    def process(self, message: Any, source: str = "text") -> Dict[str, Any]:
        """Execute exactly one turn and return a stable, serializable result."""
        text = str(message or "").strip()
        language = self.detect_language(text)
        started = time.monotonic()
        timestamp = datetime.now(timezone.utc).isoformat()

        if not text:
            result = ConversationResult(
                status=ConversationStatus.NEEDS_CLARIFICATION,
                response_text="",
                error_category="empty_message",
            )
            return self._complete(result, timestamp, source, text, language, started)

        if not self.active:
            self.start()
        self.turn_count += 1
        self.last_user_message = text

        try:
            raw_result = self._executor(text)
            # Exit is an explicit command-level outcome, not a response-text
            # heuristic.  All other legacy string responses are kept intact.
            status_hint = (
                ConversationStatus.EXIT_SESSION.name
                if text.lower() in {"exit", "quit", "shutdown vyom", "close vyom"}
                else None
            )
            result = ConversationResult.from_executor_result(raw_result, status_hint)
        except Exception as error:
            result = ConversationResult(
                status=ConversationStatus.FAILED,
                response_text="I could not process that request: " + str(error),
                error_message=str(error),
                error_category="executor_error",
            )

        return self._complete(result, timestamp, source, text, language, started)

    def _complete(self, result, timestamp, source, text, language, started):
        duration_ms = int((time.monotonic() - started) * 1000)
        self.last_response = result.response_text
        self._append_turn(ConversationTurn(
            timestamp=timestamp, source=str(source), input_text=text,
            language=language, response_text=result.response_text,
            status=result.status.value, error_category=result.error_category,
            duration_ms=duration_ms,
        ))
        return {
            "success": result.status == ConversationStatus.SUCCESS,
            "status": result.status.value,
            "message": result.response_text,
            "response": result.response_text,
            "result": result.executor_result,
            "source": source,
            "language": language,
            "turn": self.turn_count,
            "error_category": result.error_category,
            "duration_ms": duration_ms,
            "history_size": len(self.history),
        }

    def process_text(self, text: Any) -> Dict[str, Any]:
        return self.process(text, source="text")

    def process_voice(self, text: Any) -> Dict[str, Any]:
        return self.process(text, source="voice")

    def get_history(self) -> List[Dict[str, Any]]:
        return [asdict(turn) for turn in self.history]

    def get_recent_history(self, limit: int = 5) -> List[Dict[str, Any]]:
        return self.get_history()[-max(1, int(limit)):]

    def snapshot(self) -> Dict[str, Any]:
        return {
            "active": self.active, "turn_count": self.turn_count,
            "last_user_message": self.last_user_message,
            "last_response": self.last_response, "history": self.get_history(),
        }
