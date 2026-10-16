import unittest

from ai_core.context_action_compiler import ContextActionCompiler
from windows_agent.ui_element_finder import UIElementFinder
from windows_agent.ui_grounder import UIElementGrounder
from windows_agent import ui_patterns


class FakeElement:
    def __init__(self):
        self.calls = []

    def invoke(self):
        self.calls.append("invoke")
        return "invoked"

    def click(self):
        self.calls.append("click")
        return "clicked"

    def set_focus(self):
        self.calls.append("focus")
        return "focused"

    def set_value(self, value):
        self.calls.append(("set_value", value))
        return True


class FakeFinder:
    def __init__(self, element):
        self.element = element
        self.query = None

    def find_best(self, **kwargs):
        self.query = kwargs
        return {
            "element": self.element,
            "info": {
                "name": "Search",
                "control_type": "Button",
                "automation_id": "searchButton",
            },
        }


class Phase2UIAutomationTests(unittest.TestCase):

    def test_ui_patterns_are_generic(self):
        element = FakeElement()
        self.assertEqual(ui_patterns.click(element), "clicked")
        self.assertEqual(ui_patterns.invoke(element), "invoked")
        self.assertEqual(ui_patterns.focus(element), "focused")
        self.assertTrue(ui_patterns.set_value(element, "Hello"))
        self.assertIn(("set_value", "Hello"), element.calls)

    def test_invoke_uses_only_the_explicit_invoke_pattern(self):
        class ClickOnlyElement:
            def __init__(self):
                self.calls = []

            def click(self):
                self.calls.append("click")

        element = ClickOnlyElement()
        self.assertIsNone(ui_patterns.select_operation(element, "invoke"))
        self.assertFalse(ui_patterns.supported_operations(element)["invoke"])
        with self.assertRaises(AttributeError):
            ui_patterns.invoke(element)
        self.assertEqual(element.calls, [])

    def test_operation_selection_prefers_semantic_methods(self):
        element = FakeElement()
        self.assertEqual(ui_patterns.select_operation(element, "invoke"), "invoke")
        self.assertEqual(ui_patterns.select_operation(element, "click"), "click")
        self.assertEqual(ui_patterns.select_operation(element, "focus"), "set_focus")
        self.assertEqual(ui_patterns.select_operation(element, "set_value"), "set_value")

        class InvokeOnlyElement:
            def invoke(self):
                return "invoked"

        self.assertEqual(ui_patterns.select_operation(InvokeOnlyElement(), "click"), "invoke")
        self.assertEqual(ui_patterns.select_operation(InvokeOnlyElement(), "invoke"), "invoke")

    def test_operation_result_records_selected_dispatch_method(self):
        payload = ui_patterns.operation_result(
            success=True,
            operation="invoke_ui_element",
            method="invoke",
        )
        self.assertEqual(payload["dispatch_method"], "invoke")

    def test_grounder_uses_ui_automation_properties(self):
        element = FakeElement()
        finder = FakeFinder(element)
        grounder = UIElementGrounder(finder=finder)

        result = grounder.ground(
            "Search",
            {
                "automation_id": "searchButton",
                "control_type": "Button",
                "window_title": "Example",
            },
        )

        self.assertTrue(result["success"])
        self.assertIs(result["element"], element)
        self.assertEqual(finder.query["automation_id"], "searchButton")
        self.assertEqual(finder.query["control_type"], "Button")
        self.assertEqual(finder.query["window_title"], "Example")
        self.assertIn("supported_operations", result)
        self.assertTrue(result["supported_operations"]["invoke"])
    def test_unsupported_invoke_pattern_fails_before_dispatch(self):
        from windows_agent.ui_automation import WindowsUICapability

        class ClickOnlyElement:
            def __init__(self):
                self.calls = []

            def click(self):
                self.calls.append("click")

        element = ClickOnlyElement()

        class Grounder:
            def ground(self, target, args):
                return {
                    "success": True,
                    "element": element,
                    "element_info": {"name": target, "control_type": "Button"},
                }

        provider = WindowsUICapability(ui_grounder=Grounder())
        result = provider._invoke_ui_element({
            "action": "invoke_ui_element",
            "target": "Submit",
        })

        self.assertFalse(result["success"])
        self.assertEqual(result["stage"], "ui_pattern_unsupported")
        self.assertEqual(element.calls, [])

    def test_grounder_accepts_semantic_name_variation(self):
        class RankedFinder:
            def find_ranked(self, **kwargs):
                return [{
                    "element": object(),
                    "info": {
                        "name": "Search",
                        "control_type": "Button",
                        "automation_id": "searchButton",
                    },
                    "score": 0.81,
                }]

        grounder = UIElementGrounder(finder=RankedFinder())
        result = grounder.ground("search box")
        self.assertTrue(result["success"])
        self.assertGreaterEqual(result["confidence"], 0.80)

    def test_grounder_rejects_ambiguous_semantic_target(self):
        class RankedFinder:
            def find_ranked(self, **kwargs):
                return [
                    {
                        "element": object(),
                        "info": {"name": "Search", "control_type": "Button"},
                        "score": 0.72,
                    },
                    {
                        "element": object(),
                        "info": {"name": "Search", "control_type": "Edit"},
                        "score": 0.70,
                    },
                ]

        grounder = UIElementGrounder(finder=RankedFinder())
        result = grounder.ground("search")
        self.assertFalse(result["success"])
        self.assertEqual(result["stage"], "ui_target_ambiguous")

    def test_control_type_filter_does_not_bypass_near_tie_ambiguity(self):
        class RankedFinder:
            def find_ranked(self, **kwargs):
                self.query = kwargs
                return [
                    {
                        "element": object(),
                        "info": {"name": "Search", "control_type": "Button", "enabled": True, "visible": True},
                        "score": 0.91,
                    },
                    {
                        "element": object(),
                        "info": {"name": "Search", "control_type": "Button", "automation_id": "otherSearch", "enabled": True, "visible": True},
                        "score": 0.89,
                    },
                ]

        finder = RankedFinder()
        grounder = UIElementGrounder(finder=finder)
        result = grounder.ground("Search", {"control_type": "Button"})

        self.assertFalse(result["success"])
        self.assertEqual(result["stage"], "ui_target_ambiguous")
        self.assertEqual(finder.query["control_type"], "Button")

    def test_hidden_high_score_candidate_is_not_chosen_over_visible_candidate(self):
        visible = object()

        class RankedFinder:
            def find_ranked(self, **kwargs):
                return [
                    {
                        "element": object(),
                        "info": {"name": "Search", "visible": False, "enabled": True},
                        "score": 0.99,
                    },
                    {
                        "element": visible,
                        "info": {"name": "Search", "visible": True, "enabled": True},
                        "score": 0.80,
                    },
                ]

        result = UIElementGrounder(finder=RankedFinder()).ground("Search")

        self.assertTrue(result["success"])
        self.assertIs(result["element"], visible)

    def test_disabled_only_candidate_is_not_actionable(self):
        class RankedFinder:
            def find_ranked(self, **kwargs):
                return [{
                    "element": object(),
                    "info": {"name": "Search", "visible": True, "enabled": False},
                    "score": 0.99,
                }]

        result = UIElementGrounder(finder=RankedFinder()).ground("Search")

        self.assertFalse(result["success"])
        self.assertEqual(result["stage"], "ui_element_unavailable")

    def test_invalid_candidate_score_is_handled_without_crashing(self):
        class RankedFinder:
            def find_ranked(self, **kwargs):
                return [{
                    "element": object(),
                    "info": {"name": "Search", "visible": True, "enabled": True},
                    "score": float("nan"),
                }]

        result = UIElementGrounder(finder=RankedFinder()).ground("Search")

        self.assertFalse(result["success"])
        self.assertEqual(result["stage"], "ui_target_ambiguous")

    def test_finder_is_safe_when_uia_is_unavailable(self):
        finder = UIElementFinder()
        if not finder.is_available():
            self.assertEqual(finder.find(name="Search"), [])

    def test_semantic_click_compiles_to_generic_ui_action(self):
        compiler = ContextActionCompiler()
        result = compiler.compile(
            goal="click Search",
            context={"current_target": "current window"},
        )
        self.assertTrue(result["complete"])
        self.assertEqual(result["plan"][0]["action"], "click_ui_element")
        self.assertEqual(result["plan"][0]["target"], "Search")

    def test_coordinate_click_remains_legacy_fallback(self):
        compiler = ContextActionCompiler()
        result = compiler.compile(
            goal="click 100,200",
            context={"current_target": "current window"},
        )
        self.assertTrue(result["complete"])
        self.assertEqual(result["plan"][0]["action"], "click")
        self.assertEqual(result["plan"][0]["args"]["x"], 100)
        self.assertEqual(result["plan"][0]["args"]["y"], 200)


    def test_execute_refuses_target_when_observed_identity_changed(self):
        from windows_agent.ui_automation import WindowsUICapability

        element = FakeElement()

        class Grounder:
            calls = 0

            def ground(self, target, args=None):
                self.calls += 1
                return {
                    "success": True,
                    "element": element,
                    "element_info": {
                        "name": "Search",
                        "control_type": "Button",
                        "automation_id": "searchButton",
                    },
                }

        class Observer:
            calls = 0

            def snapshot(self, action=None, primary_element=None):
                self.calls += 1
                return {
                    "available": True,
                    "active_window": {"exists": True, "name": "Example", "hwnd": 7},
                    "focused_element": {"exists": True, "name": "Editor"},
                    "target_element": {
                        "exists": True,
                        "name": "Other",
                        "control_type": "Button",
                        "automation_id": "searchButton",
                        "window_identity": {"name": "Example", "hwnd": 7},
                    },
                    "ui_tree_signature": [{"name": "Search"}],
                }

        grounder = Grounder()
        observer = Observer()
        provider = WindowsUICapability(ui_grounder=grounder, ui_observer=observer)
        result = provider.execute({"action": "click_ui_element", "target": "Search"})

        self.assertFalse(result["success"])
        self.assertEqual(result["stage"], "ui_target_context_mismatch")
        self.assertEqual(element.calls, [])
        self.assertEqual(grounder.calls, 1)
        self.assertEqual(observer.calls, 1)

    def test_execute_refuses_target_from_different_active_window(self):
        from windows_agent.ui_automation import WindowsUICapability

        element = FakeElement()

        class Grounder:
            def ground(self, target, args=None):
                return {
                    "success": True,
                    "element": element,
                    "element_info": {
                        "name": "Search",
                        "control_type": "Button",
                        "automation_id": "searchButton",
                    },
                }

        class Observer:
            def snapshot(self, action=None, primary_element=None):
                return {
                    "available": True,
                    "active_window": {"exists": True, "name": "Example", "hwnd": 7},
                    "focused_element": {"exists": True, "name": "Editor"},
                    "target_element": {
                        "exists": True,
                        "name": "Search",
                        "control_type": "Button",
                        "automation_id": "searchButton",
                        "window_identity": {"name": "Another Window", "hwnd": 99},
                    },
                    "ui_tree_signature": [{"name": "Search"}],
                }

        provider = WindowsUICapability(ui_grounder=Grounder(), ui_observer=Observer())
        result = provider.execute({"action": "click_ui_element", "target": "Search"})

        self.assertFalse(result["success"])
        self.assertEqual(result["stage"], "ui_target_window_mismatch")
        self.assertEqual(element.calls, [])

    def test_same_grounded_element_is_observed_before_and_after_action(self):
        from windows_agent.ui_automation import WindowsUICapability

        element = FakeElement()

        class Grounder:
            calls = 0

            def ground(self, target, args=None):
                self.calls += 1
                return {
                    "success": True,
                    "element": element,
                    "element_info": {
                        "name": "Search",
                        "control_type": "Button",
                        "automation_id": "searchButton",
                    },
                }

        class Observer:
            def __init__(self):
                self.elements = []

            def snapshot(self, action=None, primary_element=None):
                self.elements.append(primary_element)
                after = len(self.elements) > 1
                return {
                    "available": True,
                    "active_window": {"exists": True, "name": "Example", "hwnd": 7},
                    "focused_element": {"exists": True, "name": "Search" if after else "Editor"},
                    "target_element": {
                        "exists": True,
                        "name": "Search",
                        "control_type": "Button",
                        "automation_id": "searchButton",
                        "focused": after,
                        "window_identity": {"name": "Example", "hwnd": 7},
                    },
                    "ui_tree_signature": [{"name": "Search", "focused": after}],
                }

        grounder = Grounder()
        observer = Observer()
        provider = WindowsUICapability(ui_grounder=grounder, ui_observer=observer)
        result = provider.execute({"action": "focus_ui_element", "target": "Search"})

        self.assertTrue(result["success"], result.get("message"))
        self.assertTrue(result.get("verification", {}).get("verified"))
        self.assertEqual(grounder.calls, 1)
        self.assertEqual(len(observer.elements), 2)
        self.assertIs(observer.elements[0], element)
        self.assertIs(observer.elements[1], element)
        self.assertIn("focus", element.calls)


if __name__ == "__main__":
    unittest.main()
