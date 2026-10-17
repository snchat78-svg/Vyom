"""M6.4 end-to-end tests for the uncertain-action recovery boundary.

These tests use a deterministic fake UI snapshot/action executor. They exercise
the real command_engine.execute -> AutonomousAgent recovery -> MissionRuntime
path without sending real keystrokes or network messages.
"""
import time

import pytest

from ai_core.autonomous_agent import AutonomousAgent
from command_engine import executor


def _agent_with_uncertain_send():
    agent = AutonomousAgent(max_steps=5)
    agent.current_goal = "send message"
    agent.mission_runtime.start("send message", [{
        "id": "send_once",
        "step": 1,
        "type": "action",
        "action": "invoke_ui_element",
        "capability": "windows_ui",
        "target": "Send",
        "args": {},
        "depends_on": [],
    }])
    step = agent.mission_runtime.get_next_step()
    retry, policy = agent._record_step_failure(step, {
        "success": False,
        "stage": "verification_failed",
        "message": "post-action observer unavailable",
        "result": {
            "success": False,
            "stage": "verification_failed",
            "verification": {
                "verified": False,
                "verification_level": "post_action_observation_failed",
            },
        },
        "verification": {
            "verified": False,
            "verification_level": "post_action_observation_failed",
        },
    })
    assert retry is False
    assert policy["category"] == "outcome_uncertain"
    assert agent.mission_runtime.snapshot()["replay_lock"]["active"] is True
    return agent


def _fresh_ui_observation(**kwargs):
    now = time.time()
    return {
        "phase": kwargs.get("phase", "test"),
        "world_state": {
            "timestamp": now,
            "ui": {"available": True, "timestamp": now},
            "current_window": {"title": "Chat"},
            "focused_control": {"name": "Message"},
        },
    }


def test_executor_lock_intercepts_unrelated_commands_before_normal_routing(monkeypatch):
    agent = _agent_with_uncertain_send()
    monkeypatch.setattr(executor, "autonomous_agent", agent)
    monkeypatch.setattr(
        executor.intent_engine,
        "detect",
        lambda *args, **kwargs: pytest.fail("intent detection must not bypass active recovery"),
    )
    monkeypatch.setattr(
        executor.goal_router,
        "route",
        lambda *args, **kwargs: pytest.fail("goal routing must not bypass active recovery"),
    )
    monkeypatch.setattr(
        executor.tool_manager,
        "execute",
        lambda *args, **kwargs: pytest.fail("no tool may execute before recovery is resolved"),
    )

    result = executor.execute("open calculator")

    assert result["success"] is False
    assert result["status"] == "needs_confirmation"
    assert result["stage"] == "recovery_confirmation_required"
    assert result["requires_user_input"] is True
    assert "cancel recovery" in result["message"].lower()
    assert agent.mission_runtime.snapshot()["replay_lock"]["active"] is True


def test_executor_cancel_resolves_lock_without_dispatch_or_retry(monkeypatch):
    agent = _agent_with_uncertain_send()
    monkeypatch.setattr(executor, "autonomous_agent", agent)
    monkeypatch.setattr(
        executor.intent_engine,
        "detect",
        lambda *args, **kwargs: pytest.fail("cancel should be handled before intent detection"),
    )
    monkeypatch.setattr(
        executor.tool_manager,
        "execute",
        lambda *args, **kwargs: pytest.fail("cancel must not dispatch the pending action"),
    )

    result = executor.execute("cancel recovery")

    assert result["success"] is False
    assert result["status"] == "cancelled"
    assert result["stage"] == "recovery_cancelled"
    assert agent.mission_runtime.snapshot()["replay_lock"] is None
    assert not any(
        event.get("event") == "step_retry"
        for event in agent.mission_runtime.history
    )


def test_executor_retry_is_blocked_when_live_ui_observation_is_unavailable(monkeypatch):
    agent = _agent_with_uncertain_send()
    agent._observe_cycle = lambda **kwargs: {
        "phase": kwargs.get("phase", "recovery_confirmation"),
        "world_state": {
            "timestamp": time.time(),
            "ui": {"available": False},
        },
    }
    agent._continue_replanned_mission = lambda **kwargs: pytest.fail(
        "continuation must not start without fresh live UI observation"
    )
    monkeypatch.setattr(executor, "autonomous_agent", agent)
    monkeypatch.setattr(
        executor.intent_engine,
        "detect",
        lambda *args, **kwargs: pytest.fail("recovery reply should be intercepted"),
    )
    monkeypatch.setattr(
        executor.tool_manager,
        "execute",
        lambda *args, **kwargs: pytest.fail("no action may run without live UI"),
    )

    result = executor.execute("nahi hua, dobara karo")

    assert result["success"] is False
    assert result["status"] == "needs_confirmation"
    assert result["stage"] == "recovery_confirmation_required"
    assert "retry" in result["message"].lower()
    assert agent.mission_runtime.snapshot()["replay_lock"]["active"] is True


def test_confirmed_retry_reports_success_only_after_verified_completion(monkeypatch):
    agent = _agent_with_uncertain_send()
    agent._observe_cycle = _fresh_ui_observation
    dispatched = []

    def simulated_execute(step):
        dispatched.append(step["id"])
        return {
            "success": True,
            "stage": "action_dispatched",
            "result": {"success": True, "stage": "action_result"},
            "verification": {
                "verified": True,
                "verification_level": "post_action_observation",
            },
        }

    agent._execute_step = simulated_execute
    monkeypatch.setattr(executor, "autonomous_agent", agent)
    monkeypatch.setattr(
        executor.intent_engine,
        "detect",
        lambda *args, **kwargs: pytest.fail("recovery reply should be intercepted"),
    )

    result = executor.execute("nahi hua, dobara karo")

    assert result["success"] is True
    assert result["status"] == "success"
    assert result["stage"] == "recovery_retry_completed"
    assert dispatched == ["send_once"]
    assert agent.mission_runtime.snapshot()["mission_state"] == "completed"
    assert agent.mission_runtime.snapshot()["replay_lock"] is None
    assert any(
        event.get("event") == "uncertain_outcome_replay_authorized"
        for event in agent.mission_runtime.history
    )


def test_success_flag_without_verified_postcondition_relocks_recovery(monkeypatch):
    agent = _agent_with_uncertain_send()
    agent._observe_cycle = _fresh_ui_observation
    dispatched = []

    def simulated_execute(step):
        dispatched.append(step["id"])
        return {
            "success": True,
            "stage": "action_dispatched",
            "result": {"success": True, "stage": "action_result"},
            "verification": {
                "verified": False,
                "verification_level": "post_action_observation_failed",
            },
        }

    agent._execute_step = simulated_execute
    monkeypatch.setattr(executor, "autonomous_agent", agent)
    monkeypatch.setattr(
        executor.intent_engine,
        "detect",
        lambda *args, **kwargs: pytest.fail("recovery reply should be intercepted"),
    )

    result = executor.execute("nahi hua, dobara karo")

    assert result["success"] is False
    assert result["status"] == "needs_confirmation"
    assert result["stage"] == "recovery_confirmation_required"
    assert dispatched == ["send_once"]
    assert agent.mission_runtime.snapshot()["replay_lock"]["active"] is True
    assert agent.mission_runtime.snapshot()["mission_state"] == "blocked"
    assert "couldn't verify" in result["message"].lower() or "verify" in result["message"].lower()
