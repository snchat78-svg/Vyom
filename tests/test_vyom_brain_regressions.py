import unittest

from ai_core.semantic_brain import LocalSemanticBrain
from tools.tool_manager import ToolManager
from windows_agent.ui_verifier import UIVerificationEngine
from ai_core.web_knowledge import WebKnowledge


class _WindowManager:
    def __init__(self, window):
        self.window = window
    def get_foreground(self):
        return dict(self.window)


class _FakeResponse:
    def __init__(self, value):
        self.value = value.encode("utf-8")
    def read(self):
        return self.value
    def __enter__(self):
        return self
    def __exit__(self, *_args):
        return False


class VyomBrainRegressionTests(unittest.TestCase):
    def test_explicit_multiword_application_search_is_compiled_generically(self):
        result = LocalSemanticBrain().reason("gugal krom men yutyub sarch karo", context={})
        self.assertEqual(result["route"], "mission")
        self.assertEqual(result["plan"][0]["action"], "open_application")
        self.assertEqual(result["plan"][0]["target"], "gugal krom")
        self.assertEqual([step["action"] for step in result["plan"][-3:]], ["hotkey", "type_text", "keypress"])
        self.assertEqual(result["plan"][-2]["args"]["text"], "yutyub")

    def test_compound_arithmetic_has_expected_result_postcondition(self):
        result = LocalSemanticBrain().reason("Calculator kholo aur usme 25 + 25 add karo", context={})
        self.assertEqual(result["route"], "mission")
        self.assertEqual(result["semantic_interpretation"][0]["expression"], "25+25")
        self.assertEqual(result["semantic_interpretation"][0]["expected_result"], "50")
        verification = result["plan"][-1]["metadata"]["verification"]
        self.assertEqual(verification["mode"], "all")
        self.assertEqual(verification["checks"], [{"kind": "contains_visible_text", "value": "50"}])

    def test_type_text_can_verify_a_changed_non_editable_ui_surface(self):
        engine = UIVerificationEngine()
        action = {"action": "type_text", "target": "focused_element", "args": {"text": "25+25"}}
        before = {"focused_element": {"exists": False}, "ui_tree_signature": [{"name": "Display is 0", "control_type": "Text"}]}
        after = {"focused_element": {"exists": False}, "ui_tree_signature": [{"name": "Display is 25+25", "control_type": "Text"}]}
        result = engine.verify(action, before, after, {"success": True})
        self.assertTrue(result["verified"])
        self.assertEqual(result["mode"], "any")

    def test_expected_result_verification_requires_visible_text(self):
        engine = UIVerificationEngine()
        action = {"action": "keypress", "target": "enter", "metadata": {"verification": {
            "mode": "all", "checks": [{"kind": "contains_visible_text", "value": "50"}]}}}
        before = {"ui_tree_signature": [{"name": "Display is 25+25"}]}
        after = {"ui_tree_signature": [{"name": "Display is 50"}]}
        self.assertTrue(engine.verify(action, before, after, {"success": True})["verified"])
        self.assertFalse(engine.verify(action, before, {"ui_tree_signature": [{"name": "Display is 25+25"}]}, {"success": True})["verified"])

    def test_opening_the_foreground_application_reuses_it(self):
        manager = ToolManager.__new__(ToolManager)
        manager.window_manager = _WindowManager({"title": "Calculator", "hwnd": 42})
        manager._open_target_legacy = lambda _target: self.fail("Active application must not launch again.")
        result = manager._open_target("Calculator", structured=True)
        self.assertTrue(result["success"])
        self.assertEqual(result["stage"], "verified")
        self.assertEqual(result["verification"]["method"], "existing_foreground_match")
        self.assertTrue(result["result"]["reused_existing_window"])

    def test_noisy_app_target_matches_a_title_segment_without_an_alias_table(self):
        manager = ToolManager.__new__(ToolManager)
        self.assertTrue(manager._foreground_matches_target("gugal krom", {"title": "New Tab - Google Chrome"}))

    def test_webpage_extraction_is_bounded_and_cites_the_source(self):
        paragraph = (
            "The report explains the published results and methodology in detail. "
            "Its central finding is that the measured value was 42 units under the "
            "documented test conditions. The accompanying section describes the "
            "scope, limitations, and date of collection for readers."
        )
        def opener(request, timeout=0):
            self.assertLessEqual(timeout, 2.0)
            return _FakeResponse("<html><head><title>Official Test Report</title>"
                "<meta name='description' content='A public report summary.'>"
                "</head><body><nav>navigation boilerplate</nav><h1>Results</h1><p>" +
                paragraph + "</p><script>ignore this string</script></body></html>")
        result = WebKnowledge(opener=opener)._extract_webpage("https://example.com/report", "en")
        self.assertTrue(result["success"])
        self.assertIn("measured value was 42 units", result["answer"])
        self.assertIn("Official Test Report", result["answer"])
        self.assertEqual(result["source"]["url"], "https://example.com/report")
        self.assertFalse(WebKnowledge._is_public_web_url("http://127.0.0.1/private"))

    def test_webpage_extraction_does_not_follow_local_urls(self):
        calls = []
        def opener(request, timeout=0):
            calls.append(request.full_url)
            return _FakeResponse("<html><body><p>This should never be read.</p></body></html>")
        client = WebKnowledge(opener=opener)
        self.assertIsNone(client._extract_webpage("http://localhost/private", "en"))
        self.assertEqual(calls, [])


if __name__ == "__main__":
    unittest.main()
