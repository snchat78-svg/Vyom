"""
Project : Vyom AI
Version : 1.1
Module  : Mission Runtime

Purpose:
    Runtime state machine for autonomous missions.

Architecture:

    Goal
      |
      v
    MissionPlanner
      |
      v
    MissionRuntime
      |
      +----> next step
      |
      v
    ToolManager
      |
      v
    Observation / Verification
      |
      +----> completed
      |
      +----> retry
      |
      +----> replan
      |
      +----> blocked

Important:

    - MissionRuntime NEVER executes computer actions directly.
    - ToolManager remains the actual executor.
    - Runtime owns mission/step lifecycle.
    - Runtime tracks dependencies.
    - Runtime tracks retries.
    - Runtime supports verification results.
    - Runtime can request re-planning after failure.
    - Runtime supports capability-blocked missions.
    - Runtime is bounded by max_steps.
    - Runtime preserves mission history.
"""

import hashlib
import json
import math
import os
import re
import tempfile
import time
from pathlib import Path

from typing import Any, Dict, List, Optional

from ai_core.mission_plan_guard import MissionPlanGuard


class MissionRuntime:

    # =========================================================
    # TERMINAL STATES
    # =========================================================

    TERMINAL_STATES = {
        "completed",
        "failed",
        "blocked"
    }

    # =========================================================
    # INITIALIZE
    # =========================================================

    def __init__(
        self,
        max_retries: int = 2,
        max_steps: int = 10
    ):

        self.max_retries = max(
            0,
            int(max_retries)
        )

        self.max_steps = max(
            1,
            int(max_steps)
        )

        # -----------------------------------------------------
        # MISSION
        # -----------------------------------------------------

        self.goal = ""

        self.plan: List[
            Dict[str, Any]
        ] = []

        self.mission_state = "idle"

        # An unresolved post-dispatch outcome must not be replayed by a
        # model-generated re-plan. Only explicit replay authorization may clear
        # this mission-scoped lock; the stored fingerprint is hashed so action
        # payloads are not exposed in snapshots/history.
        self.replay_lock: Optional[Dict[str, Any]] = None

        # Persistence is configured only by the desktop entry point. Tests and
        # embedded callers remain isolated unless they explicitly opt in.
        self._recovery_journal_path: Optional[Path] = None
        self._recovery_journal_status = "disabled"
        self._recovery_restored_after_restart = False

        # -----------------------------------------------------
        # CURRENT STEP
        # -----------------------------------------------------

        self.current_step: Optional[
            Dict[str, Any]
        ] = None

        # -----------------------------------------------------
        # EXECUTION
        # -----------------------------------------------------

        self.step_count = 0

        self.completed_steps = 0

        self.failed_steps = 0

        # -----------------------------------------------------
        # HISTORY
        # -----------------------------------------------------

        self.history: List[
            Dict[str, Any]
        ] = []

        # -----------------------------------------------------
        # LAST RESULT
        # -----------------------------------------------------

        self.last_result: Any = None

        self.last_verification: Dict[
            str,
            Any
        ] = {}

        self.last_error = ""

        # -----------------------------------------------------
        # REPLANNING
        # -----------------------------------------------------

        self.replan_requested = False

        self.replan_reason = ""

        # -----------------------------------------------------
        # CAPABILITY
        # -----------------------------------------------------

        self.blocked_capability = None

    # =========================================================
    # RECOVERY JOURNAL (M6.5)
    # =========================================================

    def configure_default_recovery_journal(self) -> str:
        """Enable a private, per-user recovery marker for the desktop app."""
        if os.name == "nt":
            root = os.environ.get("LOCALAPPDATA") or str(
                Path.home() / "AppData" / "Local"
            )
            path = Path(root) / "Vyom" / "recovery_state.json"
        else:
            root = os.environ.get("XDG_STATE_HOME") or str(
                Path.home() / ".local" / "state"
            )
            path = Path(root) / "vyom" / "recovery_state.json"
        return self.configure_recovery_journal(path)

    def configure_recovery_journal(self, path: Any) -> str:
        """Load a minimal marker; missing/corrupt state is handled fail-closed."""
        self._recovery_journal_path = Path(path).expanduser()
        self._recovery_restored_after_restart = False

        if not self._recovery_journal_path.exists():
            self._recovery_journal_status = "clear"
            return self._recovery_journal_status

        try:
            record = json.loads(
                self._recovery_journal_path.read_text(encoding="utf-8")
            )
        except Exception:
            self._restore_recovery_lock(
                category="recovery_journal_unreadable",
                fingerprint_sha256=None,
            )
            self._recovery_journal_status = "read_failed"
            self._persist_replay_lock()
            return self._recovery_journal_status

        if (
            isinstance(record, dict)
            and record.get("schema_version") == 1
            and record.get("active") is False
        ):
            self._recovery_journal_status = "clear"
            return self._recovery_journal_status

        valid_categories = {
            "outcome_uncertain",
            "unknown_outcome",
            "recovery_journal_unreadable",
        }
        category = record.get("category") if isinstance(record, dict) else None
        fingerprint = (
            record.get("fingerprint_sha256")
            if isinstance(record, dict)
            else None
        )
        fingerprint_valid = (
            fingerprint is None
            or (
                isinstance(fingerprint, str)
                and re.fullmatch(r"[0-9a-f]{64}", fingerprint) is not None
            )
        )

        if not (
            isinstance(record, dict)
            and record.get("schema_version") == 1
            and record.get("active") is True
            and category in valid_categories
            and fingerprint_valid
        ):
            self._restore_recovery_lock(
                category="recovery_journal_unreadable",
                fingerprint_sha256=None,
            )
            self._persist_replay_lock()
            return self._recovery_journal_status

        self._restore_recovery_lock(
            category=category,
            fingerprint_sha256=fingerprint,
        )
        self._recovery_journal_status = "active"
        return self._recovery_journal_status

    def _restore_recovery_lock(
        self,
        *,
        category: str,
        fingerprint_sha256: Optional[str],
    ) -> None:
        """Restore a blocker, not a runnable mission; no plan/action is persisted."""
        self.replay_lock = {
            "active": True,
            "step_id": "recovered_after_restart",
            "category": category,
            "fingerprint_sha256": fingerprint_sha256,
            "runtime_record_available": False,
            "restored_after_restart": True,
        }
        self._recovery_restored_after_restart = True
        self.mission_state = "blocked"
        self.current_step = None
        self.last_error = (
            "A recovery marker survived the previous session. The original "
            "mission plan was not stored, so retry is unavailable until the "
            "uncertain state is explicitly resolved."
        )
        self.history.append({
            "event": "recovery_journal_restored",
            "category": category,
            "fingerprint_sha256": fingerprint_sha256,
            "runtime_record_available": False,
        })

    def _persist_replay_lock(self) -> None:
        """Atomically persist only metadata needed to keep recovery fail-closed."""
        path = self._recovery_journal_path
        lock = self.replay_lock
        if path is None or not (
            isinstance(lock, dict) and lock.get("active") is True
        ):
            return

        category = str(lock.get("category") or "unknown_outcome")
        if category not in {
            "outcome_uncertain",
            "unknown_outcome",
            "recovery_journal_unreadable",
        }:
            category = "unknown_outcome"

        fingerprint = lock.get("fingerprint_sha256")
        if not (
            isinstance(fingerprint, str)
            and re.fullmatch(r"[0-9a-f]{64}", fingerprint)
        ):
            fingerprint = None

        # Intentionally omit step IDs, goals, targets, action names, arguments,
        # typed text, clipboard contents and the plan itself.
        record = {
            "schema_version": 1,
            "active": True,
            "category": category,
            "fingerprint_sha256": fingerprint,
            "created_at": time.time(),
        }
        temporary_path = None
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                dir=str(path.parent),
                prefix=".vyom-recovery-",
                suffix=".tmp",
                delete=False,
            ) as stream:
                temporary_path = stream.name
                json.dump(
                    record,
                    stream,
                    ensure_ascii=True,
                    separators=(",", ":"),
                    allow_nan=False,
                )
                stream.flush()
                os.fsync(stream.fileno())
            try:
                os.chmod(temporary_path, 0o600)
            except OSError:
                # Windows ACLs govern the user's LocalAppData directory.
                pass
            os.replace(temporary_path, path)
            temporary_path = None
            self._recovery_journal_status = "active"
        except Exception as error:
            self._recovery_journal_status = "write_failed"
            self.history.append({
                "event": "recovery_journal_write_failed",
                "error_type": type(error).__name__,
            })
        finally:
            if temporary_path:
                try:
                    os.unlink(temporary_path)
                except OSError:
                    pass

    def _clear_recovery_journal(self) -> None:
        path = self._recovery_journal_path
        self._recovery_restored_after_restart = False
        if path is None:
            self._recovery_journal_status = "disabled"
            return
        try:
            path.unlink(missing_ok=True)
            self._recovery_journal_status = "clear"
        except Exception as error:
            # A stale marker on disk is conservative: it may ask for recovery
            # again on the next launch, but it can never cause a replay.
            self._recovery_journal_status = "clear_failed"
            self.history.append({
                "event": "recovery_journal_clear_failed",
                "error_type": type(error).__name__,
            })

    # =========================================================
    # START MISSION
    # =========================================================

    def start(
        self,
        goal: str,
        plan: List[Dict[str, Any]]
    ) -> Dict[str, Any]:

        if isinstance(self.replay_lock, dict) and self.replay_lock.get("active") is True:
            reason = (
                "A previous action outcome is uncertain. Resolve the recovery "
                "confirmation before starting another mission."
            )
            self.last_error = reason
            self.mission_state = "blocked"
            self.history.append({
                "event": "mission_start_rejected_replay_lock",
                "step_id": self.replay_lock.get("step_id"),
                "category": self.replay_lock.get("category"),
                "reason": reason,
            })
            return self.snapshot()

        self.goal = str(
            goal or ""
        ).strip()

        validation_error = MissionPlanGuard.validate(plan, self.max_steps)
        if not self.goal:
            validation_error = "Mission goal is empty."

        self.plan = []
        if validation_error is None:
            for step in plan:
                clean = dict(step)
                clean["status"] = "pending"
                for field in (
                    "result", "verification", "reused_verified_step_id",
                    "last_result", "last_error", "retries",
                ):
                    clean.pop(field, None)
                clean["depends_on"] = [
                    str(value).strip()
                    for value in clean.get("depends_on", [])
                ]
                self.plan.append(clean)

        self.current_step = None

        self.step_count = 0

        self.completed_steps = 0

        self.failed_steps = 0

        self.history = []

        self.last_result = None

        self.last_verification = {}

        self.last_error = ""

        self.replan_requested = False

        self.replan_reason = ""

        self.blocked_capability = None

        if validation_error:
            self.mission_state = "blocked"
            self.last_error = validation_error
            self.history.append({
                "event": "mission_rejected",
                "reason": validation_error,
            })
        elif not self.plan:
            self.mission_state = "blocked"
            self.last_error = "Mission plan is empty."
        else:
            self.mission_state = "ready"
            self.history.append({
                "event": "mission_started",
                "plan_size": len(self.plan),
            })

        return self.snapshot()

    # =========================================================
    # IS ACTIVE
    # =========================================================

    def is_active(
        self
    ) -> bool:

        return (
            self.mission_state
            not in self.TERMINAL_STATES
            and
            self.mission_state != "idle"
        )

    # =========================================================
    # IS TERMINAL
    # =========================================================

    def is_terminal(
        self
    ) -> bool:

        return (
            self.mission_state
            in self.TERMINAL_STATES
        )

    # =========================================================
    # GET NEXT STEP
    # =========================================================

    def get_next_step(
        self
    ) -> Optional[
        Dict[str, Any]
    ]:

        # -----------------------------------------------------
        # STOP CONDITIONS
        # -----------------------------------------------------

        if self.mission_state in (
            "idle",
            "completed",
            "failed",
            "blocked"
        ):
            return None

        # -----------------------------------------------------
        # SAFETY LIMIT
        # -----------------------------------------------------

        if self.step_count >= self.max_steps:

            self.mission_state = "failed"

            self.last_error = (
                "Mission step limit reached."
            )

            self.history.append({
                "event": "safety_limit",
                "step_count": self.step_count,
                "max_steps": self.max_steps
            })

            return None

        # -----------------------------------------------------
        # CHECK REPLAN
        # -----------------------------------------------------

        if self.replan_requested:

            return None

        # -----------------------------------------------------
        # COMPLETED STEP IDS
        # -----------------------------------------------------

        completed_ids = {
            str(
                item.get("id")
            )
            for item in self.plan
            if item.get(
                "status"
            ) == "completed"
        }

        # -----------------------------------------------------
        # FIND READY STEP
        # -----------------------------------------------------

        for step in self.plan:

            status = step.get(
                "status",
                "pending"
            )

            if status != "pending":
                continue

            dependencies = step.get(
                "depends_on",
                []
            )

            if not isinstance(
                dependencies,
                list
            ):

                dependencies = []

            dependencies_ready = all(
                str(dep)
                in completed_ids
                for dep in dependencies
            )

            if not dependencies_ready:

                continue

            # -------------------------------------------------
            # PREPARE STEP
            # -------------------------------------------------

            step["status"] = "executing"

            self.current_step = step

            self.mission_state = "executing"

            self.step_count += 1

            self.history.append({
                "event": "step_started",
                "step": step.get(
                    "step"
                ),
                "id": step.get(
                    "id"
                ),
                "step_count": self.step_count
            })

            return step

        # -----------------------------------------------------
        # CHECK MISSION COMPLETION
        # -----------------------------------------------------

        if self.plan and all(
            step.get(
                "status"
            ) == "completed"
            for step in self.plan
        ):

            self.mission_state = "completed"

            self.current_step = None

            self.history.append({
                "event": "mission_completed"
            })

            return None

        # -----------------------------------------------------
        # NO EXECUTABLE STEP
        #
        # This usually means:
        #
        # - dependency problem
        # - blocked plan
        # - invalid mission
        # -----------------------------------------------------

        pending_steps = [
            step
            for step in self.plan
            if step.get(
                "status",
                "pending"
            ) == "pending"
        ]

        if pending_steps:

            self.mission_state = "blocked"

            self.last_error = (
                "No executable mission step "
                "is currently available."
            )

            self.history.append({
                "event": "mission_blocked",
                "reason": self.last_error
            })

        return None

    # =========================================================
    # MARK STEP COMPLETED
    # =========================================================

    def mark_completed(
        self,
        step_id: str,
        result: Any = None,
        verification: Optional[
            Dict[str, Any]
        ] = None
    ) -> bool:

        step = self._find_step(
            step_id
        )

        if step is None:
            return False

        is_current = (
            isinstance(self.current_step, dict)
            and str(self.current_step.get("id") or "") == str(step_id)
            and str(step.get("status") or "") == "executing"
        )
        if not is_current:
            reason = "Only the currently executing mission step can be completed."
            self.last_error = reason
            self.history.append({
                "event": "step_completion_rejected",
                "id": str(step_id),
                "reason": reason,
            })
            return False

        verified = (
            isinstance(verification, dict)
            and verification.get("verified") is True
        )
        if not verified:
            reason = "Step completion rejected because its postcondition was not verified."
            self.last_result = result
            self.last_verification = (
                dict(verification) if isinstance(verification, dict) else {}
            )
            self.last_error = reason
            step["status"] = "failed"
            step["result"] = result
            step["verification"] = self.last_verification
            step["last_error"] = reason
            self.failed_steps += 1
            self.current_step = None

            # The executor reported success, but the postcondition was not
            # observed. Treat that as a possible completed side effect, not
            # a normal planning failure. Lock it before a new plan can replay it.
            fingerprint = self._step_fingerprint(step)
            digest = (
                hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()
                if isinstance(fingerprint, str)
                else None
            )
            self.replay_lock = {
                "active": True,
                "step_id": str(step_id),
                "category": "outcome_uncertain",
                "fingerprint_sha256": digest,
                "runtime_record_available": True,
                "restored_after_restart": False,
            }
            self._persist_replay_lock()
            self.replan_requested = False
            self.replan_reason = ""
            self.mission_state = "blocked"
            self.history.append({
                "event": "step_completion_rejected",
                "id": str(step_id),
                "reason": reason,
                "verification": self.last_verification,
                "replay_lock": dict(self.replay_lock),
            })
            self.history.append({
                "event": "mission_blocked_after_unverified_completion",
                "step_id": str(step_id),
                "category": "outcome_uncertain",
                "fingerprint_sha256": digest,
            })
            return False

        # -----------------------------------------------------
        # UPDATE STEP
        # -----------------------------------------------------

        step["status"] = "completed"

        step["result"] = result

        step["verification"] = (
            verification or {}
        )

        # -----------------------------------------------------
        # UPDATE RUNTIME
        # -----------------------------------------------------

        self.completed_steps += 1

        self.last_result = result

        self.last_verification = (
            verification or {}
        )

        self.last_error = ""

        # -----------------------------------------------------
        # HISTORY
        # -----------------------------------------------------

        self.history.append({
            "event": "step_completed",
            "step": step.get(
                "step"
            ),
            "id": step_id,
            "status": "completed",
            "result": result,
            "verification": (
                verification or {}
            )
        })

        self.current_step = None

        # -----------------------------------------------------
        # CHECK MISSION COMPLETE
        # -----------------------------------------------------

        if self.plan and all(
            item.get(
                "status"
            ) == "completed"
            for item in self.plan
        ):

            self.mission_state = "completed"

            self.history.append({
                "event": "mission_completed"
            })

        else:

            self.mission_state = "ready"

        return True

    # =========================================================
    # MARK STEP FAILED
    # =========================================================

    def mark_failed(
        self,
        step_id: str,
        result: Any = None,
        reason: str = "",
        verification: Optional[
            Dict[str, Any]
        ] = None,
        retryable: Optional[bool] = None,
        failure_policy: Optional[Dict[str, Any]] = None,
        stop_mission: bool = False,
    ) -> bool:

        step = self._find_step(
            step_id
        )

        if step is None:

            return False

        retries = int(
            step.get(
                "retries",
                0
            )
        )

        self.last_result = result

        self.last_verification = (
            verification or {}
        )

        self.last_error = str(
            reason or "Step failed."
        )
        policy = dict(failure_policy) if isinstance(failure_policy, dict) else {}
        if policy:
            step["failure_policy"] = policy

        # -----------------------------------------------------
        # RETRY AVAILABLE
        # -----------------------------------------------------

        if retries < self.max_retries and retryable is not False and not stop_mission:

            retries += 1

            step["retries"] = retries

            step["status"] = "pending"

            step["last_error"] = (
                self.last_error
            )

            step["last_result"] = result

            step["verification"] = (
                verification or {}
            )

            self.history.append({
                "event": "step_retry",
                "step": step.get(
                    "step"
                ),
                "id": step_id,
                "status": "retry",
                "attempt": retries,
                "result": result,
                "verification": (
                    verification or {}
                ),
                "failure_policy": policy,
                "reason": self.last_error
            })

            self.current_step = None

            self.mission_state = "ready"

            return True

        # -----------------------------------------------------
        # RETRIES EXHAUSTED
        # -----------------------------------------------------

        step["status"] = "failed"

        step["result"] = result

        step["last_error"] = (
            self.last_error
        )

        step["verification"] = (
            verification or {}
        )

        self.failed_steps += 1

        self.history.append({
            "event": "step_failed",
            "step": step.get(
                "step"
            ),
            "id": step_id,
            "status": "failed",
            "result": result,
            "verification": (
                verification or {}
            ),
            "failure_policy": policy,
            "reason": self.last_error
        })

        self.current_step = None

        # -----------------------------------------------------
        # BLOCK OR REQUEST REPLAN
        # -----------------------------------------------------

        if stop_mission:
            self.mission_state = "blocked"
            self.replan_requested = False
            self.replan_reason = ""
            self.last_error = str(
                policy.get("user_message") or self.last_error
            )

            # M6.2: preserve a runtime-enforced replay lock when dispatch may
            # already have happened. This guard lives below the agent loop so
            # direct/reasoner callers cannot bypass the uncertainty stop.
            category = str(policy.get("category") or "").strip().lower()
            if category in {"outcome_uncertain", "unknown_outcome"}:
                fingerprint = self._step_fingerprint(step)
                digest = (
                    hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()
                    if isinstance(fingerprint, str)
                    else None
                )
                self.replay_lock = {
                    "active": True,
                    "step_id": str(step_id),
                    "category": category,
                    "fingerprint_sha256": digest,
                    "runtime_record_available": True,
                    "restored_after_restart": False,
                }
                self._persist_replay_lock()

            self.history.append({
                "event": "mission_blocked_after_failure",
                "reason": self.last_error,
                "failure_policy": policy,
                "replay_lock": dict(self.replay_lock) if self.replay_lock else None,
            })
        else:
            self.request_replan(
                reason=self.last_error
            )

        return False

    # =========================================================
    # REQUEST REPLAN
    # =========================================================

    def request_replan(
        self,
        reason: str = ""
    ):

        self.replan_requested = True

        self.replan_reason = str(
            reason or ""
        ).strip()

        self.mission_state = "replanning"

        self.history.append({
            "event": "replan_requested",
            "reason": self.replan_reason
        })

    # =========================================================
    # CHECK REPLAN
    # =========================================================

    def needs_replan(
        self
    ) -> bool:

        if self.replan_requested:

            return True

        if self.mission_state == "replanning":

            return True

        for step in self.plan:

            if step.get(
                "status"
            ) == "failed":

                return True

        return False

    # =========================================================
    # APPLY NEW PLAN
    # =========================================================

    @staticmethod
    def _step_fingerprint(step: Dict[str, Any]):
        """Return a stable logical identity for a mission step.

        Execution IDs, status, retries and dependencies are intentionally
        excluded so a semantically identical step with a new model-generated
        id can inherit a previously verified completion.
        """
        if not isinstance(step, dict):
            return None

        payload = {
            "type": str(step.get("type") or "").strip().lower(),
            "action": str(step.get("action") or "").strip().lower(),
            "capability": str(step.get("capability") or "").strip().lower(),
            "target": str(step.get("target") or "").strip(),
            "args": step.get("args", {}),
            "intent": step.get("intent"),
        }
        try:
            return json.dumps(
                payload,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
            )
        except (TypeError, ValueError):
            return None

    def apply_replan(
        self,
        plan: List[
            Dict[str, Any]
        ]
    ) -> bool:

        # A plan cannot erase an unresolved action outcome. Require explicit
        # caller/user authorization through unblock() before accepting any
        # re-plan while a possible side effect is unresolved.
        if isinstance(self.replay_lock, dict) and self.replay_lock.get("active") is True:
            reason = (
                "Re-planning is blocked because a previous action may already "
                "have taken effect. Confirm the current state and explicitly "
                "authorize replay before continuing."
            )
            self.last_error = reason
            self.history.append({
                "event": "replan_rejected_replay_lock",
                "step_id": self.replay_lock.get("step_id"),
                "category": self.replay_lock.get("category"),
                "reason": reason,
            })
            return False

        validation_error = MissionPlanGuard.validate(plan, self.max_steps)
        if validation_error:
            self.mission_state = "blocked"
            self.last_error = "Re-planning rejected: " + validation_error
            self.current_step = None
            self.replan_requested = False
            self.replan_reason = ""
            self.history.append({
                "event": "replan_rejected",
                "reason": self.last_error,
            })
            return False

        # Preserve already verified logical steps across a re-plan even
        # when the model gives them a different step id. Matching is one-to-one
        # so an intentional repeated action is not collapsed into one step.
        verified_by_fingerprint = {}
        for previous_step in self.plan:
            if previous_step.get("status") != "completed":
                continue
            previous_verification = previous_step.get("verification")
            if not (
                isinstance(previous_verification, dict)
                and previous_verification.get("verified") is True
            ):
                continue
            fingerprint = self._step_fingerprint(previous_step)
            if fingerprint is None:
                continue
            verified_by_fingerprint.setdefault(fingerprint, []).append(previous_step)

        new_plan = []

        for step in plan:

            if not isinstance(
                step,
                dict
            ):
                continue

            new_step = dict(step)
            # Ignore status/result claims from reasoners. Only matching verified
            # history owned by this runtime can mark a replanned step completed.
            new_step["status"] = "pending"
            for field in (
                "result", "verification", "reused_verified_step_id",
                "last_result", "last_error", "retries",
            ):
                new_step.pop(field, None)
            new_step["depends_on"] = [
                str(value).strip()
                for value in new_step.get("depends_on", [])
            ]

            fingerprint = self._step_fingerprint(new_step)
            matches = verified_by_fingerprint.get(fingerprint, [])
            if fingerprint is not None and matches:
                previous = matches.pop(0)
                new_step["status"] = "completed"
                new_step["result"] = previous.get("result")
                new_step["verification"] = dict(previous.get("verification") or {})
                new_step["reused_verified_step_id"] = previous.get("id")

            new_plan.append(
                new_step
            )

        if not new_plan:

            self.mission_state = "blocked"

            self.last_error = (
                "Re-planning produced an empty plan."
            )

            return False

        self.plan = new_plan

        # Recompute plan-derived counters after verified-step carry-forward.
        self.completed_steps = sum(
            1 for item in self.plan
            if item.get("status") == "completed"
        )
        self.failed_steps = sum(
            1 for item in self.plan
            if item.get("status") == "failed"
        )

        self.current_step = None

        self.replan_requested = False

        self.replan_reason = ""

        self.mission_state = "ready"

        self.history.append({
            "event": "plan_updated",
            "plan_size": len(
                self.plan
            )
        })

        return True

    # =========================================================
    # BLOCK MISSION
    # =========================================================

    def block(
        self,
        reason: str = "",
        capability: Any = None
    ):

        self.mission_state = "blocked"

        self.last_error = str(
            reason or "Mission blocked."
        )

        self.blocked_capability = (
            capability
        )

        self.current_step = None

        self.history.append({
            "event": "mission_blocked",
            "reason": self.last_error,
            "capability": capability
        })

    # =========================================================
    # UNBLOCK
    # =========================================================

    def unblock(
        self,
        *,
        allow_replay_after_confirmation: bool = False,
    ) -> bool:
        """Unblock a mission; replay of an uncertain action needs explicit consent."""
        if (
            isinstance(self.replay_lock, dict)
            and self.replay_lock.get("active") is True
            and self.replay_lock.get("runtime_record_available") is False
            and allow_replay_after_confirmation is True
        ):
            self.last_error = (
                "Recovery was restored after restart without the original mission record. "
                "Retry is disabled; resolve the uncertain state or cancel recovery."
            )
            self.history.append({
                "event": "mission_unblock_rejected_missing_runtime_record",
                "category": self.replay_lock.get("category"),
                "reason": self.last_error,
            })
            return False

        if not self.plan:
            return False

        if isinstance(self.replay_lock, dict) and self.replay_lock.get("active") is True:
            if allow_replay_after_confirmation is not True:
                self.last_error = (
                    "Mission remains blocked: a previous action outcome is uncertain. "
                    "Confirm the current window and explicitly authorize replay first."
                )
                self.history.append({
                    "event": "mission_unblock_rejected_replay_lock",
                    "step_id": self.replay_lock.get("step_id"),
                    "category": self.replay_lock.get("category"),
                    "reason": self.last_error,
                })
                return False

            lock = dict(self.replay_lock)
            step = self._find_step(str(lock.get("step_id") or ""))
            if not isinstance(step, dict) or step.get("status") != "failed":
                self.last_error = (
                    "The uncertain step cannot be replayed because its failed runtime record is unavailable."
                )
                self.history.append({
                    "event": "mission_unblock_rejected_missing_step",
                    "step_id": lock.get("step_id"),
                    "reason": self.last_error,
                })
                return False

            step["status"] = "pending"
            for field in ("result", "verification", "last_result", "last_error"):
                step.pop(field, None)
            self.failed_steps = max(0, self.failed_steps - 1)
            self.history.append({
                "event": "uncertain_outcome_replay_authorized",
                "step_id": lock.get("step_id"),
                "category": lock.get("category"),
                "fingerprint_sha256": lock.get("fingerprint_sha256"),
            })
            self.replay_lock = None
            self._clear_recovery_journal()

        self.blocked_capability = None
        self.last_error = ""
        self.replan_requested = False
        self.replan_reason = ""
        self.current_step = None
        self.mission_state = "ready"
        self.history.append({"event": "mission_unblocked"})
        return True

    def resolve_uncertain_outcome(self, resolution: str) -> bool:
        """Resolve a replay lock without retrying when the user says it happened or cancels."""
        if not (
            isinstance(self.replay_lock, dict)
            and self.replay_lock.get("active") is True
        ):
            return False

        normalized = str(resolution or "").strip().lower()
        if normalized not in {"already_applied", "cancelled"}:
            return False

        lock = dict(self.replay_lock)
        self.replay_lock = None
        self._clear_recovery_journal()
        self.current_step = None
        self.replan_requested = False
        self.replan_reason = ""
        self.mission_state = "failed"
        self.last_error = (
            "User confirmed the action had already taken effect; the mission was stopped without replay."
            if normalized == "already_applied"
            else "User cancelled recovery; the mission was stopped without replay."
        )
        self.history.append({
            "event": "uncertain_outcome_resolved",
            "resolution": normalized,
            "step_id": lock.get("step_id"),
            "category": lock.get("category"),
            "fingerprint_sha256": lock.get("fingerprint_sha256"),
        })
        return True

    # =========================================================
    # FIND STEP
    # =========================================================

    def _find_step(
        self,
        step_id: str
    ) -> Optional[
        Dict[str, Any]
    ]:

        wanted = str(
            step_id
        )

        for step in self.plan:

            if str(
                step.get("id")
            ) == wanted:

                return step

        return None

    # =========================================================
    # GET CURRENT STEP
    # =========================================================

    def get_current_step(
        self
    ) -> Optional[
        Dict[str, Any]
    ]:

        if not isinstance(
            self.current_step,
            dict
        ):

            return None

        return dict(
            self.current_step
        )

    # =========================================================
    # GET STEP
    # =========================================================

    def get_step(
        self,
        step_id: str
    ) -> Optional[
        Dict[str, Any]
    ]:

        step = self._find_step(
            step_id
        )

        if step is None:

            return None

        return dict(
            step
        )

    # =========================================================
    # MISSION PROGRESS
    # =========================================================

    def progress(
        self
    ) -> Dict[str, Any]:

        total = len(
            self.plan
        )

        completed = sum(
            1
            for step in self.plan
            if step.get(
                "status"
            ) == "completed"
        )

        failed = sum(
            1
            for step in self.plan
            if step.get(
                "status"
            ) == "failed"
        )

        pending = sum(
            1
            for step in self.plan
            if step.get(
                "status"
            ) == "pending"
        )

        executing = sum(
            1
            for step in self.plan
            if step.get(
                "status"
            ) == "executing"
        )

        percentage = (
            (completed / total) * 100
            if total
            else 0
        )

        return {
            "total": total,
            "completed": completed,
            "failed": failed,
            "pending": pending,
            "executing": executing,
            "percentage": percentage
        }

    # =========================================================
    # SNAPSHOT
    # =========================================================

    def snapshot(
        self
    ) -> Dict[str, Any]:

        return {
            "goal": self.goal,

            "mission_state": (
                self.mission_state
            ),

            "replay_lock": (
                dict(self.replay_lock)
                if isinstance(self.replay_lock, dict)
                else None
            ),

            "recovery_journal_status": self._recovery_journal_status,
            "recovery_restored_after_restart": self._recovery_restored_after_restart,

            "current_step": (
                dict(
                    self.current_step
                )
                if isinstance(
                    self.current_step,
                    dict
                )
                else None
            ),

            "plan": [
                dict(step)
                for step in self.plan
            ],

            "history": [
                dict(item)
                for item in self.history
            ],

            "step_count": (
                self.step_count
            ),

            "max_steps": (
                self.max_steps
            ),

            "completed_steps": (
                self.completed_steps
            ),

            "failed_steps": (
                self.failed_steps
            ),

            "last_result": (
                self.last_result
            ),

            "last_verification": (
                dict(
                    self.last_verification
                )
            ),

            "last_error": (
                self.last_error
            ),

            "replan_requested": (
                self.replan_requested
            ),

            "replan_reason": (
                self.replan_reason
            ),

            "blocked_capability": (
                self.blocked_capability
            ),

            "progress": (
                self.progress()
            )
        }

    # =========================================================
    # RESET
    # =========================================================

    def reset(
        self
    ):

        self.goal = ""

        self.plan = []

        self.mission_state = "idle"

        self.current_step = None

        self.step_count = 0

        self.completed_steps = 0

        self.failed_steps = 0

        self.history = []

        self.last_result = None

        self.last_verification = {}

        self.last_error = ""

        self.replan_requested = False

        self.replan_reason = ""

        self.blocked_capability = None
        # Explicit session reset clears the in-memory lock and its durable marker.
        self.replay_lock = None
        self._clear_recovery_journal()
