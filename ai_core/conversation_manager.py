"""Lightweight voice/text façade over Vyom's existing executor.

Conversation history is bounded presentation history only.  The persistent
execution context continues to live in executor -> AutonomousAgent ->
SessionMemory.
"""

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import inspect
import time
import uuid
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
            "trace_id": uuid.uuid4().hex,
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
    def _find_mapping(root: Any, key: str, depth: int = 0) -> Optional[Dict[str, Any]]:
        if depth > 3 or not isinstance(root, dict):
            return None
        value = root.get(key)
        if isinstance(value, dict):
            return value
        for child_key in ("result", "execution_result", "details"):
            child = root.get(child_key)
            found = ConversationManager._find_mapping(child, key, depth + 1)
            if found is not None:
                return found
        return None

    @staticmethod
    def _compact_pipeline_trace(trace_sink: Any) -> Dict[str, Any]:
        if not isinstance(trace_sink, dict):
            return {}
        compact: Dict[str, Any] = {}
        trace_id = trace_sink.get("trace_id")
        if isinstance(trace_id, str):
            compact["trace_id"] = trace_id[:64]
        intent = trace_sink.get("intent")
        if isinstance(intent, dict):
            compact["intent"] = {
                "type": str(intent.get("type") or "unknown")[:80],
                "target_present": bool(intent.get("target_present")),
                "selection_present": bool(intent.get("selection_present")),
                "hypothesis_count": min(16, max(0, int(intent.get("hypothesis_count") or 0))),
            }
            confidence = ConversationManager._safe_confidence(intent.get("confidence"))
            if confidence is not None:
                compact["intent"]["confidence"] = confidence
        route = trace_sink.get("route")
        if isinstance(route, dict):
            compact["route"] = {
                "name": str(route.get("name") or "unknown")[:80],
                "reason": str(route.get("reason") or "")[:120],
                "goal": bool(route.get("goal")),
            }
        path = trace_sink.get("routing_path")
        if isinstance(path, str):
            compact["routing_path"] = path[:80]

        evidence = trace_sink.get("observation_evidence")
        if isinstance(evidence, dict):
            events = []
            supplied_events = evidence.get("events")
            if isinstance(supplied_events, list):
                for item in supplied_events[-12:]:
                    if not isinstance(item, dict):
                        continue
                    event: Dict[str, Any] = {}
                    timestamp = item.get("timestamp")
                    if isinstance(timestamp, (int, float)) and not isinstance(timestamp, bool):
                        numeric_timestamp = float(timestamp)
                        if numeric_timestamp == numeric_timestamp and numeric_timestamp not in (float("inf"), float("-inf")):
                            event["timestamp"] = round(numeric_timestamp, 3)
                    for key, limit in (
                        ("phase", 80), ("step_type", 64), ("status", 80),
                        ("stage", 80), ("state", 80), ("verification_level", 80),
                    ):
                        value = item.get(key)
                        if isinstance(value, str):
                            event[key] = value[:limit]
                    for key in ("world_snapshot_available", "result_success"):
                        if isinstance(item.get(key), bool):
                            event[key] = item[key]
                    verification_status = item.get("verification_status")
                    if verification_status in {"verified", "failed", "not_reported"}:
                        event["verification_status"] = verification_status
                    events.append(event)

            event_count = evidence.get("event_count")
            if not isinstance(event_count, int) or isinstance(event_count, bool):
                event_count = len(events)
            compact["observation_evidence"] = {
                "available": evidence.get("available") is True,
                "status": str(evidence.get("status") or "unknown")[:80],
                "event_count": min(500, max(0, event_count)),
                "events": events,
            }
            if isinstance(evidence.get("trace_id"), str):
                compact["observation_evidence"]["trace_id"] = evidence["trace_id"][:64]
        return compact

    @staticmethod
    def _mission_summary(raw: Dict[str, Any]) -> Dict[str, Any]:
        mission = ConversationManager._find_mapping(raw, "mission")
        if not isinstance(mission, dict):
            return {"available": False}

        plan = mission.get("plan")
        plan = plan if isinstance(plan, list) else []
        counts = {"pending": 0, "executing": 0, "completed": 0, "failed": 0, "blocked": 0}
        for step in plan[:500]:
            if not isinstance(step, dict):
                continue
            status = str(step.get("status") or "").strip().lower()
            if status in counts:
                counts[status] += 1
        progress = mission.get("progress")
        if isinstance(progress, dict):
            for key in ("total", "completed", "failed", "pending", "executing"):
                value = progress.get(key)
                if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
                    counts[key] = value

        # M0 exit-gate audit: preserve useful plan topology without copying
        # action payloads, target names, step IDs, or condition contents.
        allowed_step_types = {
            "action", "execute_existing_intent", "capability", "generic_action",
            "reasoning", "decision", "observation", "wait", "user_input",
            "clarification", "control_flow", "subgoal", "sub_goal", "plan",
        }
        allowed_step_statuses = {
            "pending", "executing", "completed", "failed", "blocked",
            "skipped", "cancelled", "waiting", "needs_confirmation",
        }
        plan_step_limit = 16
        plan_steps = []
        for position, step in enumerate(plan[:plan_step_limit], start=1):
            if not isinstance(step, dict):
                continue
            raw_type = str(step.get("type") or step.get("step_type") or "").strip().lower()
            raw_status = str(step.get("status") or "").strip().lower()
            dependencies = step.get("depends_on")
            plan_steps.append({
                "position": position,
                "type": raw_type if raw_type in allowed_step_types else "other",
                "status": raw_status if raw_status in allowed_step_statuses else "other",
                "dependency_count": len(dependencies) if isinstance(dependencies, list) else 0,
                "precondition_present": any(
                    key in step and step.get(key) is not None
                    for key in ("precondition", "preconditions", "requires")
                ),
                "postcondition_present": any(
                    key in step and step.get(key) is not None
                    for key in ("postcondition", "postconditions", "completion_criteria", "expected_state")
                ),
            })

        replay_lock = mission.get("replay_lock")
        return {
            "available": True,
            "state": str(mission.get("mission_state") or "unknown")[:80],
            "step_count": len(plan),
            "step_status_counts": counts,
            "plan_steps": plan_steps,
            "plan_steps_truncated": len(plan) > plan_step_limit,
            "current_step_present": isinstance(mission.get("current_step"), dict),
            "replay_lock_active": bool(
                isinstance(replay_lock, dict) and replay_lock.get("active") is True
            ),
            "recovery_journal_status": str(mission.get("recovery_journal_status") or "")[:40] or None,
        }

    @staticmethod
    def _goal_compilation_summary(raw: Dict[str, Any]) -> Dict[str, Any]:
        compilation = ConversationManager._find_mapping(raw, "goal_compilation")
        if not isinstance(compilation, dict):
            return {"available": False}
        sub_goals = compilation.get("sub_goals")
        suggested = compilation.get("suggested_intents")
        return {
            "available": True,
            "success": compilation.get("success") if isinstance(compilation.get("success"), bool) else None,
            "understood": compilation.get("understood") if isinstance(compilation.get("understood"), bool) else None,
            "complexity": str(compilation.get("complexity") or "unknown")[:40],
            "sub_goal_count": len(sub_goals) if isinstance(sub_goals, list) else 0,
            "suggested_intent_count": len(suggested) if isinstance(suggested, list) else 0,
            "suggested_intent_types": [
                str(item.get("intent") or "unknown")[:80]
                for item in (suggested[:16] if isinstance(suggested, list) else [])
                if isinstance(item, dict)
            ],
        }

    @staticmethod
    def _context_summary(raw: Dict[str, Any]) -> Dict[str, Any]:
        context = ConversationManager._find_mapping(raw, "context")
        if not isinstance(context, dict):
            return {"available": False}
        return {
            "available": True,
            "current_app_present": bool(context.get("current_app")),
            "current_file_present": bool(context.get("current_file")),
            "current_target_present": bool(context.get("current_target")),
            "pending_selection": bool(context.get("pending_selection")),
            "awaiting_confirmation": bool(context.get("awaiting_confirmation")),
            "task_state_present": bool(context.get("task_state")),
        }

    @staticmethod
    def _accepts_keyword(function: Callable[..., Any], keyword: str) -> bool:
        try:
            parameters = inspect.signature(function).parameters.values()
        except (TypeError, ValueError):
            return False
        return any(
            parameter.name == keyword or parameter.kind == inspect.Parameter.VAR_KEYWORD
            for parameter in parameters
        )

    @staticmethod
    def _update_execution_trace(
        trace: Dict[str, Any],
        conversation_result: ConversationResult,
        trace_sink: Optional[Dict[str, Any]] = None,
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
        trace["pipeline"] = ConversationManager._compact_pipeline_trace(trace_sink)
        trace["goal_compilation"] = ConversationManager._goal_compilation_summary(raw)
        trace["mission"] = ConversationManager._mission_summary(raw)
        trace["context"] = ConversationManager._context_summary(raw)

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
        trace_sink: Dict[str, Any] = {"trace_id": trace["trace_id"]}

        if not text:
            result = ConversationResult(
                status=ConversationStatus.NEEDS_CLARIFICATION,
                response_text="",
                error_category="empty_message",
            )
            self._update_execution_trace(trace, result, trace_sink)
            return self._complete(result, timestamp, source, text, language, started, trace)

        if not self.active:
            self.start()
        self.turn_count += 1
        self.last_user_message = text
        trace["turn"] = self.turn_count

        try:
            kwargs: Dict[str, Any] = {}
            if metadata is not None and self._accepts_keyword(self._executor, "metadata"):
                kwargs["metadata"] = metadata
            if self._accepts_keyword(self._executor, "trace_sink"):
                kwargs["trace_sink"] = trace_sink
            raw_result = self._executor(text, **kwargs)

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

        self._update_execution_trace(trace, result, trace_sink)
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
