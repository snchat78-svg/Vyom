"""
Project : Vyom AI
Version : 1.0
Module  : UI-enabled Autonomous Agent

Purpose:
    Add the Step 2 generic Windows UI capability to the existing
    AutonomousAgent without rewriting or duplicating its mature legacy
    open/file/process execution path.

The base agent remains the compatibility core. This subclass intercepts
only generic action steps; all legacy steps continue through the existing
implementation unchanged.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from ai_core.action_validator import ActionValidator
from ai_core.autonomous_agent import AutonomousAgent
from ai_core.capability_executor import CapabilityExecutor
from ai_core.capability_registry import CapabilityRegistry
from ai_core.capability_resolver import CapabilityResolver
from windows_agent.ui_automation import WindowsUICapability


class UIAutonomousAgent(AutonomousAgent):
    """Existing autonomous agent extended with a generic Windows UI provider."""

    def __init__(
        self,
        tool_manager=None,
        brain=None,
        reasoning_engine=None,
        max_steps: int = 10,
    ):
        super().__init__(
            tool_manager=tool_manager,
            brain=brain,
            reasoning_engine=reasoning_engine,
            max_steps=max_steps,
        )

        validator = getattr(self.reasoning_engine, "action_validator", None)
        if not isinstance(validator, ActionValidator):
            validator = ActionValidator(max_steps=max_steps)

        registry = getattr(self.reasoning_engine, "capability_registry", None)
        if not isinstance(registry, CapabilityRegistry):
            registry = CapabilityRegistry()
            try:
                self.reasoning_engine.capability_registry = registry
                self.reasoning_engine.capability_resolver = CapabilityResolver(registry)
            except Exception:
                pass

        self.action_validator = validator
        self.capability_executor = CapabilityExecutor(
            registry=registry,
            validator=validator,
        )
        self.ui_capability = WindowsUICapability()
        self.capability_executor.register(self.ui_capability, enabled=True, priority=50)

    def _execute_step(self, step):
        if not isinstance(step, dict):
            return super()._execute_step(step)

        step_type = str(step.get("type") or "").strip().lower()
        if step_type != "action":
            return super()._execute_step(step)

        if self.step_count >= self.max_steps:
            return {
                "success": False,
                "stage": "safety_limit",
                "message": "Autonomous step limit reached.",
            }

        validation = self.action_validator.validate_action(
            step,
            index=int(step.get("step", self.step_count + 1) or 1),
        )
        if not validation.get("valid", False):
            return {
                "success": False,
                "stage": "action_validation_failed",
                "message": validation.get("error", "Invalid generic action."),
                "step": step,
            }

        action = validation["action"]
        self.step_count += 1

        self.context.record_action({
            "type": "action",
            "action": action,
            "step": step,
        })

        result = self.capability_executor.execute(action)
        verification = result.get("verification", {}) if isinstance(result, dict) else {}
        verified = bool(verification.get("verified", False)) if isinstance(verification, dict) else False
        result_successful = bool(result.get("success", False)) if isinstance(result, dict) else bool(result)
        successful = result_successful and verified

        self.context.record_result(result, successful)
        self.task_history.append({
            "step": self.step_count,
            "type": "action",
            "action": action,
            "result": result,
            "verified": verified,
            "verification": verification,
            "result_success": result_successful,
        })

        if successful:
            return {
                "success": True,
                "stage": "verified",
                "result": result,
                "verification": verification,
                "step": self.step_count,
            }

        if result_successful and not verified:
            return {
                "success": False,
                "stage": "verification_failed",
                "result": result,
                "verification": verification,
                "step": self.step_count,
            }

        return {
            "success": False,
            "stage": str(result.get("stage", "execution_failed")) if isinstance(result, dict) else "execution_failed",
            "result": result,
            "verification": verification,
            "step": self.step_count,
        }
