"""Lightweight voice/text façade over Vyom's existing executor.

Conversation history is bounded presentation history only.  The persistent
execution context continues to live in executor -> AutonomousAgent ->
SessionMemory.
"""

from dataclasses import asdict, dataclass, field
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
    trace: Dict[str, Any] = field(default_factory=dict)


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

    @staticmethod
    def _safe_confidence(value: Any) -> Optional[float]:
        try:
            confidence = float(value)
        except (TypeError, ValueError, OverflowError):
            return None
        if confidence != confidence or confidence in (float("inf"), float("-inf")):
            return None
        return confidence if 0.0 <= confidence <= 1.0 else None

    @staticmethod
    def _safe_corrections(value: Any) -> List[Dict[str, Any]]:
        if not isinstance(value, list):
            return []
        corrections: List[Dict[str, Any]] = []
        for item in value[:16]:
            if not isinstance(item, dict):
                continue
            clean: Dict[str, Any] = {}
            for key in ("from", "to"):
                token = item.get(key)
                if isinstance(token, (str, int, float)) and not isinstance(token, bool):
                    clean[key] = str(token)[:160]
            score = ConversationManager._safe_confidence(item.get("score"))
            if score is not None:
                clean["score"] = score
            position = item.get("position")
            if isinstance(position, int) and not isinstance(position, bool) and position >= 0:
                clean["position"] = position
            if clean:
                corrections.append(clean)
        return corrections

    def _build_input_trace(
        self,
        text: str,
        source: str,
        metadata: Optional[Dict[str, Any]],
        timestamp: str,
        language: str,
    ) -> Dict[str, Any]:
        metadata = metadata if isinstance(metadata, dict) else {}
        voice = metadata.get("voice")
        voice = voice if source == "voice" and isinstance(voice, dict) else {}

        raw_transcript = str(voice.get("raw_text") or "") if voice else ""
        normalized_input = str(
            voice.get("roman_text")
            or voice.get("normalized_text")
            or text
        )
        confidence = self._safe_confidence(voice.get("command_confidence"))
        recognized_language = str(
            voice.get("recognized_language") or voice.get("language") or ""
        ).strip() or None

        try:
            alternatives_count = int(voice.get("transcription_alternatives_count") or 0) if voice else 0
        except (TypeError, ValueError, OverflowError):
            alternatives_count = 0
        alternatives_count = min(16, max(0, alternatives_count))

        return {
            "schema_version": 1,
            "timestamp": timestamp,
            "source": str(source),
            "raw_input": raw_transcript if source == "voice" and raw_transcript else text,
            "raw_transcript": raw_transcript if source == "voice" else None,
            "normalized_input": normalized_input,
            "language": language,
            "recognized_language": recognized_language,
            "stt_status": str(voice.get("stt_status") or "") or None,
            "transcription_alternatives_count": alternatives_count,
            "input_confidence": confidence,
            "input_confidence_source": "command_normalizer" if confidence is not None else None,
            "corrections": self._safe_corrections(voice.get("command_corrections")),
            "execution": {
                "success": None,
                "status": "not_run",
                "stage": None,
                "verification_status": "not_reported",
                "error_category": None,
                "duration_ms": None,
            },
        }

    @staticmethod
    def _verification_status(value: Any, depth: int = 0) -> str:
        """Find explicit verification evidence without inferring from generic success."""
        if depth > 3 or not isinstance(value, dict):
            return "not_reported"

        for key in (
            "postcondition_verified", "verification_success",
            "verification_passed", "is_verified", "verified",
        ):
            candidate = value.get(key)
            if isinstance(candidate, bool):
                return "verified" if candidate else "failed"

        verification_keys = (
            "verification", "verification_result", "last_verification",
            "postcondition_verification", "postcondition",
        )
        for key in verification_keys:
            candidate = value.get(key)
            if isinstance(candidate, bool):
                return "verified" if candidate else "failed"
            if isinstance(candidate, dict):
                for flag in ("postcondition_verified", "verification_success",
                             "verification_passed", "is_verified", "verified",
                             "success", "passed"):
                    flag_value = candidate.get(flag)
                    if isinstance(flag_value, bool):
                        return "verified" if flag_value else "failed"
                status = str(candidate.get("status") or "").strip().lower()
                if status in {"verified", "passed", "success", "succeeded"}:
                    return "verified"
                if status in {"failed", "not_verified", "unverified", "mismatch"}:
                    return "failed"
                nested = ConversationManager._verification_status(candidate, depth + 1)
                if nested != "not_reported":
                    return nested
            elif isinstance(candidate, str):
                normalized = candidate.strip().lower()
                if normalized in {"verified", "passed", "success", "succeeded"}:
                    return "verified"
                if normalized in {"failed", "not_verified", "unverified", "mismatch"}:
                    return "failed"

        for key in ("result", "mission", "execution_result", "details"):
            nested = value.get(key)
            if isinstance(nested, dict):
                status = ConversationManager._verification_status(nested, depth + 1)
                if status != "not_reported":
                    return status
        return "not_reported"

    @staticmethod
    def _update_execution_trace(
        trace: Dict[str, Any],
        conversation_result: ConversationResult,
    ) -> None:
        raw = conversation_result.executor_result
        raw = raw if isinstance(raw, dict) else {}
        execution = trace.setdefault("execution", {})
        explicit_success = raw.get("success")
        execution["success"] = (
            bool(explicit_success)
            if isinstance(explicit_success, bool)
            else conversation_result.status == ConversationStatus.SUCCESS
        )
        execution["status"] = str(
            raw.get("status") or conversation_result.status.value
        )
        execution["stage"] = str(raw.get("stage") or "") or None
        execution["error_category"] = str(
            raw.get("error_category") or conversation_result.error_category or ""
        ) or None
        execution["verification_status"] = ConversationManager._verification_status(raw)

    def process(
        self,
        message: Any,
        source: str = "text",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Execute one turn and keep a bounded, structured input/execution trace."""
        text = str(message or "").strip()
        metadata = metadata if isinstance(metadata, dict) else None
        language_text = text
        if isinstance(metadata, dict):
            voice = metadata.get("voice")
            if isinstance(voice, dict) and voice.get("raw_text"):
                language_text = str(voice.get("raw_text"))
        language = self.detect_language(language_text)
        started = time.monotonic()
        timestamp = datetime.now(timezone.utc).isoformat()
        trace = self._build_input_trace(text, source, metadata, timestamp, language)

        if not text:
            result = ConversationResult(
                status=ConversationStatus.NEEDS_CLARIFICATION,
                response_text="",
                error_category="empty_message",
            )
            self._update_execution_trace(trace, result)
            return self._complete(result, timestamp, source, text, language, started, trace)

        if not self.active:
            self.start()
        self.turn_count += 1
        self.last_user_message = text
        trace["turn"] = self.turn_count

        try:
            if metadata is not None:
                try:
                    raw_result = self._executor(text, metadata=metadata)
                except TypeError as error:
                    # Preserve compatibility with injected legacy test
                    # executors that still accept only one positional argument.
                    try:
                        raw_result = self._executor(text)
                    except TypeError:
                        raise error
            else:
                raw_result = self._executor(text)

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

        self._update_execution_trace(trace, result)
        return self._complete(result, timestamp, source, text, language, started, trace)

    def _complete(
        self,
        result: ConversationResult,
        timestamp: str,
        source: str,
        text: str,
        language: str,
        started: float,
        trace: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        duration_ms = int((time.monotonic() - started) * 1000)
        self.last_response = result.response_text
        turn_trace = dict(trace or {})
        turn_trace["duration_ms"] = duration_ms
        execution = turn_trace.setdefault("execution", {})
        execution["duration_ms"] = duration_ms
        execution.setdefault("status", result.status.value)
        if execution.get("status") == "not_run":
            execution["status"] = result.status.value
        execution["conversation_status"] = result.status.value
        self._append_turn(ConversationTurn(
            timestamp=timestamp,
            source=str(source),
            input_text=text,
            language=language,
            response_text=result.response_text,
            status=result.status.value,
            error_category=result.error_category,
            duration_ms=duration_ms,
            trace=turn_trace,
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
            "trace": turn_trace,
        }

    def process_text(
        self,
        text: Any,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        return self.process(text, source="text", metadata=metadata)

    def process_voice(
        self,
        text: Any,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        return self.process(text, source="voice", metadata=metadata)

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
