import unittest

from ai_core.reasoning_engine import ReasoningEngine


class SemanticDeepReasoner:
    """Model-backed stand-in used only to test the semantic contract."""

    def __init__(self, data):
        self.data = data
        self.calls = []

    def is_available(self):
        return True

    def reason(self, **kwargs):
        self.calls.append(kwargs)
        return {
            "success": True,
            "available": True,
            "source": "test_model",
            "data": self.data,
        }

    def reset(self):
        self.calls.clear()


class Phase5SemanticContractTests(unittest.TestCase):

    def _engine(self, goal, action, capability="windows_ui", target=""):
        reasoner = SemanticDeepReasoner({
            "understood": True,
            "goal": goal,
            "language": "hinglish",
            "complexity": "simple",
            "analysis": "semantic test",
            "route": "capability",
            "capability": capability,
            "semantic_interpretation": "resolved from the whole utterance",
            "references": [],
            "ambiguities": [],
            "plan": [{
                "step": 1,
                "id": "semantic_1",
                "type": "action",
                "description": "semantic operation",
                "action": action,
                "capability": capability,
                "target": target,
                "args": {},
                "preconditions": [],
                "postconditions": ["requested semantic operation is verified"],
                "depends_on": [],
            }],
            "needs_confirmation": False,
            "reason": "semantic plan",
        })

        engine = ReasoningEngine(deep_reasoner=reasoner)
        engine.capability_registry.register(
            capability,
            description="generic test capability",
            actions=[action],
        )
        return engine, reasoner

    def test_arbitrary_paraphrase_stays_generic(self):
        goal = "bhai woh text wala application chala do"
        engine, reasoner = self._engine(
            goal,
            action="open_application",
            target="the text application referred to by the user",
        )

        result = engine.reason(goal, context={
            "current_app": "",
            "current_target": "",
            "conversation_history": [],
        })

        self.assertEqual(result["route"]["route"], "capability")
        self.assertEqual(result["plan"][0]["type"], "action")
        self.assertEqual(result["plan"][0]["action"], "open_application")
        self.assertNotIn("intent", result["plan"][0])
        self.assertEqual(len(reasoner.calls), 1)
        self.assertEqual(reasoner.calls[0]["goal"], goal)

    def test_context_is_passed_to_semantic_reasoner_for_reference_resolution(self):
        goal = "isme mera naam likh do"
        engine, reasoner = self._engine(
            goal,
            action="type_text",
            target="current_focused_input",
        )

        context = {
            "current_app": "Notepad",
            "current_target": "Notepad editor",
            "conversation_history": [
                {"role": "user", "text": "mera naam Shambhu Lal hai"}
            ],
        }

        result = engine.reason(goal, context=context)

        self.assertEqual(result["route"]["route"], "capability")
        self.assertEqual(result["plan"][0]["action"], "type_text")
        self.assertEqual(result["plan"][0]["target"], "current_focused_input")
        self.assertEqual(reasoner.calls[0]["context"], context)

    def test_failed_step_is_replanned_from_previous_result(self):
        goal = "do the requested task again using the current state"
        engine, reasoner = self._engine(
            goal,
            action="retry_current_operation",
            target="current_state",
        )

        result = engine.reason(
            goal,
            context={"current_app": "Notepad"},
            previous_result={
                "success": False,
                "stage": "verification_failed",
                "message": "target was not in expected state",
            },
        )

        self.assertEqual(result["route"]["route"], "capability")
        self.assertEqual(
            reasoner.calls[0]["previous_result"]["stage"],
            "verification_failed",
        )
        self.assertEqual(
            result["plan"][0]["action"],
            "retry_current_operation",
        )


if __name__ == "__main__":
    unittest.main()
