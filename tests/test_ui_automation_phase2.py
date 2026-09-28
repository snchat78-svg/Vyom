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


if __name__ == "__main__":
    unittest.main()
