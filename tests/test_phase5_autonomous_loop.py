import time
import unittest

from ai_core.autonomous_agent import AutonomousAgent
from ai_core.mission_runtime import MissionRuntime


class Phase5ObservationTests(unittest.TestCase):
    def test_observation_boundary_is_serializable_and_recorded(self):
        agent = AutonomousAgent(max_steps=3)
        observation = agent._observe_cycle(
            phase="test",
            step={"id": "a1", "type": "action"},
            result={"success": True},
            verification={"verified": True},
        )
        self.assertEqual(observation["phase"], "test")
        self.assertEqual(observation["step_id"], "a1")
        self.assertIn("world_state", observation)
        self.assertGreater(observation["timestamp"], 0)
        self.assertTrue(observation["world_state"]["clipboard"]["skipped"])
        latest = observation["world_state"]["observation_history"][-1]
        self.assertEqual(latest["phase"], "test")
        self.assertEqual(latest["timestamp"], observation["timestamp"])
        self.assertNotIn("observation_history", latest["world_state"])
        self.assertFalse(
            any(
                item.get("stage") == "observation"
                for item in agent.task_history
                if isinstance(item, dict)
            )
        )
        self.assertTrue(agent.world_state.observation_history)
        self.assertEqual(
            agent.world_state.observation_history[-1]["phase"],
            "test",
        )

    def test_observation_failure_does_not_execute_or_mutate_targets(self):
        agent = AutonomousAgent(max_steps=3)
        observation = agent._observe_cycle(
            phase="before_action",
            step={"id": "a1", "type": "action", "target": "Search"},
        )
        self.assertEqual(observation["step_id"], "a1")
        self.assertEqual(
            observation["world_state"]["current_target"],
            "",
        )

    def test_replan_uses_recorded_snapshot_without_a_second_world_read(self):
        agent = AutonomousAgent(max_steps=3)
        calls = []

        class World:
            observation_history = []

            last_snapshot = None

            def snapshot(self, *args, **kwargs):
                calls.append("snapshot")
                return {
                    "timestamp": 200.0,
                    "ui": {"available": True},
                    "current_window": {"name": "Window A"},
                    "observation_history": [],
                }

            def record_observation(self, observation):
                self.observation_history.append({
                    "phase": observation["phase"],
                    "timestamp": observation["timestamp"],
                })

        agent.world_state = World()
        recorded = agent._observe_cycle(phase="before_replan")

        self.assertEqual(calls, ["snapshot"])
        self.assertIs(recorded["world_state"], agent.world_state.last_snapshot)
        self.assertEqual(recorded["world_state"]["observation_history"][-1]["phase"], "before_replan")

    def test_replan_freshness_rejects_stale_future_and_error_snapshots(self):
        now = time.time()
        fresh = {
            "timestamp": now,
            "ui": {"available": True, "timestamp": now},
        }
        self.assertTrue(AutonomousAgent._is_fresh_world_observation(fresh, now=now))
        self.assertFalse(AutonomousAgent._is_fresh_world_observation(
            {"timestamp": now - 11, "ui": {"available": True, "timestamp": now}},
            now=now,
        ))
        self.assertFalse(AutonomousAgent._is_fresh_world_observation(
            {"timestamp": now, "ui": {"available": True, "timestamp": now - 11}},
            now=now,
        ))
        self.assertFalse(AutonomousAgent._is_fresh_world_observation(
            {"timestamp": now + 3, "ui": {"available": True, "timestamp": now}},
            now=now,
        ))
        self.assertFalse(AutonomousAgent._is_fresh_world_observation(
            {"timestamp": now, "observation_error": "observer failed"},
            now=now,
        ))
        self.assertFalse(AutonomousAgent._is_fresh_world_observation(
            {"ui": {"available": True}},
            now=now,
        ))

    def test_replanning_stops_before_reasoning_when_observation_is_stale(self):
        agent = AutonomousAgent(max_steps=3)
        reason_calls = []

        class StaleWorld:
            def __init__(self):
                self.observation_history = []
                self.last_snapshot = None

            def snapshot(self, *args, **kwargs):
                old = time.time() - 60
                return {
                    "timestamp": old,
                    "ui": {"available": True, "timestamp": old},
                    "observation_history": [],
                }

            def record_observation(self, observation):
                self.observation_history.append({
                    "phase": observation.get("phase"),
                    "timestamp": observation.get("timestamp"),
                    "world_state": {},
                })

        class ReplanRuntime:
            def start(self, goal, plan):
                return {"mission_state": "running"}

            def needs_replan(self):
                return True

            def snapshot(self):
                return {"mission_state": "running", "plan": []}

        agent.world_state = StaleWorld()
        agent.mission_runtime = ReplanRuntime()
        agent.reasoning_engine.reason = lambda *args, **kwargs: reason_calls.append(args) or {}

        result = agent._run_mission(
            goal="continue task",
            plan=[{"id": "step1", "type": "action"}],
            intent=None,
            analysis={},
            compilation={},
            route={},
        )

        self.assertFalse(result["success"])
        self.assertEqual(result["stage"], "replanning_error")
        self.assertIn("stale", result["error"].lower())
        self.assertEqual(reason_calls, [])

    def test_proposed_open_intent_does_not_mutate_session_context(self):
        agent = AutonomousAgent(max_steps=3)
        agent._compile_goal = lambda goal, intent=None: {
            "suggested_intents": [
                {"intent": "open", "target": "New App", "source": "test"}
            ]
        }
        agent._run_mission = lambda **kwargs: {
            "success": False,
            "stage": "simulated_failure",
            "message": "Not opened",
        }

        result = agent.run("open New App")

        self.assertFalse(result["success"])
        self.assertIsNone(agent.context.current_app)
        self.assertIsNone(agent.context.current_target)
        self.assertIsNone(agent.context.current_file)

    def test_failed_verification_does_not_replace_last_verified_app(self):
        class ToolManager:
            def execute(self, intent):
                return {"success": True, "stage": "opened"}

        class Verifier:
            def verify(self, intent, result):
                return {"verified": False, "reason": "target window not observed"}

        agent = AutonomousAgent(tool_manager=ToolManager(), max_steps=3)
        agent.verifier = Verifier()
        agent.context.set_current_app("Previous App")
        agent.context.set_current_target("Previous App")

        result = agent._execute_step({
            "step": 1,
            "id": "open_new",
            "type": "execute_existing_intent",
            "intent": {"intent": "open", "target": "New App"},
            "depends_on": [],
            "status": "pending",
        })

        self.assertFalse(result["success"])
        self.assertEqual(agent.context.current_app, "Previous App")
        self.assertEqual(agent.context.current_target, "Previous App")

    def test_verified_open_updates_session_context(self):
        class ToolManager:
            def execute(self, intent):
                return {"success": True, "stage": "opened"}

        class Verifier:
            def verify(self, intent, result):
                return {"verified": True, "state": "observed"}

        agent = AutonomousAgent(tool_manager=ToolManager(), max_steps=3)
        agent.verifier = Verifier()

        result = agent._execute_step({
            "step": 1,
            "id": "open_app",
            "type": "execute_existing_intent",
            "intent": {"intent": "open", "target": "New App"},
            "depends_on": [],
            "status": "pending",
        })

        self.assertTrue(result["success"])
        self.assertEqual(agent.context.current_app, "New App")
        self.assertEqual(agent.context.current_target, "New App")


    def test_replan_reuses_verified_logical_step_with_new_id(self):
        runtime = MissionRuntime(max_retries=1, max_steps=5)
        runtime.start(
            goal="open and type",
            plan=[
                {
                    "step": 1,
                    "id": "old_open",
                    "type": "action",
                    "action": "open_application",
                    "capability": "windows_ui",
                    "target": "Notepad",
                    "args": {},
                    "depends_on": [],
                    "status": "pending",
                },
                {
                    "step": 2,
                    "id": "old_type",
                    "type": "action",
                    "action": "type_text",
                    "capability": "windows_ui",
                    "target": "Hello",
                    "args": {"text": "Hello"},
                    "depends_on": ["old_open"],
                    "status": "pending",
                },
            ],
        )
        runtime.get_next_step()
        runtime.mark_completed(
            "old_open",
            result={"success": True},
            verification={"verified": True},
        )

        self.assertTrue(
            runtime.apply_replan([
                {
                    "step": 10,
                    "id": "new_open",
                    "type": "action",
                    "action": "open_application",
                    "capability": "windows_ui",
                    "target": "Notepad",
                    "args": {},
                    "depends_on": [],
                },
                {
                    "step": 11,
                    "id": "new_type",
                    "type": "action",
                    "action": "type_text",
                    "capability": "windows_ui",
                    "target": "Hello",
                    "args": {"text": "Hello"},
                    "depends_on": ["new_open"],
                },
            ])
        )

        self.assertEqual(runtime.plan[0]["status"], "completed")
        self.assertEqual(runtime.plan[0]["reused_verified_step_id"], "old_open")
        self.assertEqual(runtime.get_next_step()["id"], "new_type")


    def test_runtime_rejects_malformed_start_plan_without_dropping_steps(self):
        runtime = MissionRuntime(max_steps=4)
        snapshot = runtime.start("open then type", [
            {"id": "open", "type": "action", "action": "open_application", "capability": "windows_ui", "target": "editor", "depends_on": []},
            None,
            {"id": "type", "type": "action", "action": "type_text", "capability": "windows_ui", "target": "focused_element", "args": {"text": "hello"}, "depends_on": ["open"]},
        ])
        self.assertEqual(snapshot["mission_state"], "blocked")
        self.assertEqual(snapshot["plan"], [])
        self.assertIn("not an object", snapshot["last_error"])
        self.assertIsNone(runtime.get_next_step())

    def test_runtime_never_trusts_precompleted_status_on_fresh_start(self):
        runtime = MissionRuntime(max_steps=3)
        runtime.start("one task", [{
            "id": "claimed_done",
            "type": "action",
            "action": "type_text",
            "capability": "windows_ui",
            "target": "focused_element",
            "args": {"text": "hello"},
            "depends_on": [],
            "status": "completed",
            "result": {"success": True},
            "verification": {"verified": True},
        }])
        self.assertEqual(runtime.plan[0]["status"], "pending")
        self.assertIsNone(runtime.plan[0].get("verification"))
        self.assertEqual(runtime.get_next_step()["id"], "claimed_done")

    def test_unverified_step_completion_cannot_unlock_dependent_step(self):
        runtime = MissionRuntime(max_retries=0, max_steps=3)
        runtime.start("open then type", [
            {"id": "open", "type": "action", "action": "open_application", "capability": "windows_ui", "target": "editor", "depends_on": []},
            {"id": "type", "type": "action", "action": "type_text", "capability": "windows_ui", "target": "focused_element", "args": {"text": "hello"}, "depends_on": ["open"]},
        ])
        self.assertEqual(runtime.get_next_step()["id"], "open")
        self.assertFalse(runtime.mark_completed("open", result={"success": True}, verification={"verified": False}))
        self.assertNotEqual(runtime.plan[0]["status"], "completed")
        self.assertTrue(runtime.needs_replan())
        self.assertIsNone(runtime.get_next_step())
        self.assertEqual(runtime.plan[1]["status"], "pending")

    def test_replan_rejects_unknown_dependency_atomically(self):
        runtime = MissionRuntime(max_retries=0, max_steps=4)
        runtime.start("open and type", [
            {"id": "open", "type": "action", "action": "open_application", "capability": "windows_ui", "target": "editor", "depends_on": []},
        ])
        original = [dict(item) for item in runtime.plan]
        self.assertFalse(runtime.apply_replan([
            {"id": "type", "type": "action", "action": "type_text", "capability": "windows_ui", "target": "focused_element", "args": {"text": "hello"}, "depends_on": ["unknown"]},
        ]))
        self.assertEqual(runtime.plan, original)
        self.assertEqual(runtime.mission_state, "blocked")
        self.assertIn("unknown id", runtime.last_error)

    def test_replan_does_not_trust_reasoner_supplied_completed_status(self):
        runtime = MissionRuntime(max_retries=0, max_steps=3)
        runtime.start("write greeting", [
            {"id": "old", "type": "action", "action": "type_text", "capability": "windows_ui", "target": "focused_element", "args": {"text": "hello"}, "depends_on": []},
        ])
        self.assertTrue(runtime.apply_replan([
            {"id": "new", "type": "action", "action": "type_text", "capability": "windows_ui", "target": "different_element", "args": {"text": "hello"}, "depends_on": [], "status": "completed", "verification": {"verified": True}},
        ]))
        self.assertEqual(runtime.plan[0]["status"], "pending")
        self.assertIsNone(runtime.plan[0].get("verification"))

    def test_mission_guard_rejects_dependency_cycles(self):
        from ai_core.mission_plan_guard import MissionPlanGuard
        error = MissionPlanGuard.validate([
            {"id": "first", "depends_on": ["second"]},
            {"id": "second", "depends_on": ["first"]},
        ], max_steps=3)
        self.assertIn("dependency cycle", error)



    def test_failure_policy_retries_only_proven_pre_dispatch_failures(self):
        agent = AutonomousAgent(max_steps=5)
        agent.mission_runtime.start("click target", [{
            "id": "click",
            "type": "action",
            "action": "click_ui_element",
            "capability": "windows_ui",
            "target": "Search",
            "args": {},
            "depends_on": [],
        }])
        step = agent.mission_runtime.get_next_step()
        retry, policy = agent._record_step_failure(step, {
            "success": False,
            "stage": "execution_failed",
            "result": {
                "success": False,
                "stage": "ui_target_context_mismatch",
                "message": "The target changed before dispatch.",
            },
        }, retry_observation_fresh=True)
        self.assertTrue(retry)
        self.assertEqual(policy["category"], "pre_dispatch_failure")
        self.assertEqual(agent.mission_runtime.plan[0]["status"], "pending")
        self.assertTrue(any(item.get("event") == "step_retry" for item in agent.mission_runtime.history))


    def test_pre_dispatch_retry_stops_when_recovery_observation_is_stale(self):
        agent = AutonomousAgent(max_steps=5)
        agent.mission_runtime.start("click target", [{
            "id": "click",
            "type": "action",
            "action": "click_ui_element",
            "capability": "windows_ui",
            "target": "Search",
            "args": {},
            "depends_on": [],
        }])
        step = agent.mission_runtime.get_next_step()
        retry, policy = agent._record_step_failure(step, {
            "success": False,
            "stage": "execution_failed",
            "result": {
                "success": False,
                "stage": "ui_target_context_mismatch",
                "message": "The target changed before dispatch.",
            },
        }, retry_observation_fresh=False)

        self.assertFalse(retry)
        self.assertEqual(policy["category"], "recovery_observation_unavailable")
        self.assertEqual(policy["schema_version"], "m6.1")
        self.assertEqual(agent.mission_runtime.snapshot()["mission_state"], "blocked")
        self.assertFalse(any(item.get("event") == "step_retry" for item in agent.mission_runtime.history))

    def test_recovery_observation_summary_is_fresh_and_does_not_include_ui_text(self):
        now = time.time()
        summary = AutonomousAgent._recovery_observation_summary({
            "phase": "after_failure",
            "world_state": {
                "timestamp": now,
                "ui": {"available": True, "tree_text": "private text payload"},
                "current_window": {"title": "Calculator", "password": "never copy"},
                "focused_control": {"name": "Display", "value": "25+25"},
            },
        })

        self.assertTrue(summary["fresh"])
        self.assertTrue(summary["ui_available"])
        self.assertTrue(summary["retry_ready"])
        self.assertEqual(summary["current_window"], {"title": "Calculator"})
        self.assertEqual(summary["focused_control"], {"name": "Display"})
        self.assertNotIn("private text payload", str(summary))
        self.assertNotIn("25+25", str(summary))
        self.assertNotIn("never copy", str(summary))

    def test_fresh_timestamp_without_live_ui_observation_is_not_retry_ready(self):
        now = time.time()
        summary = AutonomousAgent._recovery_observation_summary({
            "phase": "after_failure",
            "world_state": {
                "timestamp": now,
                "ui": {"available": False},
            },
        })
        self.assertTrue(summary["fresh"])
        self.assertFalse(summary["ui_available"])
        self.assertFalse(summary["retry_ready"])

    def test_runtime_rejects_replan_and_unblock_until_uncertain_replay_is_authorized(self):
        runtime = MissionRuntime(max_retries=1, max_steps=5)
        original_step = {
            "id": "send_once",
            "type": "action",
            "action": "invoke_ui_element",
            "capability": "windows_ui",
            "target": "Send",
            "args": {"message": "private message body"},
            "depends_on": [],
        }
        runtime.start("send message", [original_step])
        step = runtime.get_next_step()
        policy = {
            "category": "outcome_uncertain",
            "stop_mission": True,
            "user_message": "The result could not be verified.",
        }
        runtime.mark_failed(
            step_id=step["id"],
            result={"success": False, "stage": "verification_failed"},
            reason="verification_failed",
            verification={"verified": False},
            retryable=False,
            failure_policy=policy,
            stop_mission=True,
        )

        lock = runtime.snapshot()["replay_lock"]
        self.assertTrue(lock["active"])
        self.assertEqual(lock["step_id"], "send_once")
        self.assertEqual(lock["category"], "outcome_uncertain")
        self.assertNotIn("private message body", str(lock))

        proposed_replay = [{
            "id": "send_again",
            "type": "action",
            "action": "invoke_ui_element",
            "capability": "windows_ui",
            "target": "Send",
            "args": {"message": "private message body"},
            "depends_on": [],
        }]
        original_plan = [dict(item) for item in runtime.plan]
        self.assertFalse(runtime.apply_replan(proposed_replay))
        self.assertEqual(runtime.plan, original_plan)
        self.assertEqual(runtime.mission_state, "blocked")
        self.assertTrue(any(
            item.get("event") == "replan_rejected_replay_lock"
            for item in runtime.history
        ))

        self.assertFalse(runtime.unblock())
        self.assertTrue(runtime.snapshot()["replay_lock"]["active"])
        self.assertTrue(runtime.unblock(allow_replay_after_confirmation=True))
        self.assertIsNone(runtime.snapshot()["replay_lock"])
        self.assertTrue(runtime.apply_replan(proposed_replay))
        self.assertEqual(runtime.plan[0]["status"], "pending")
        self.assertTrue(any(
            item.get("event") == "uncertain_outcome_replay_authorized"
            for item in runtime.history
        ))

    def test_uncertain_side_effect_is_blocked_without_blind_retry(self):
        agent = AutonomousAgent(max_steps=5)
        agent.mission_runtime.start("send message", [{
            "id": "send",
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
            "result": {
                "success": False,
                "stage": "verification_failed",
                "verification": {
                    "verified": False,
                    "verification_level": "post_action_observation_failed",
                },
            },
            "verification": {"verified": False},
        })
        self.assertFalse(retry)
        self.assertEqual(policy["category"], "outcome_uncertain")
        self.assertEqual(agent.mission_runtime.snapshot()["mission_state"], "blocked")
        self.assertFalse(any(item.get("event") == "step_retry" for item in agent.mission_runtime.history))


if __name__ == "__main__":
    unittest.main()
