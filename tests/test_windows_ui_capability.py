import unittest

from ai_core.action_validator import ActionValidator
from ai_core.capability_executor import CapabilityExecutor
from ai_core.capability_registry import CapabilityRegistry
from windows_agent.ui_automation import WindowsUICapability


class FakeWindowManager:
    def focus(self, **kwargs):
        return {
            "success": True,
            "stage": "window_focused",
            "window": {"hwnd": 42, "title": kwargs.get("target", ""), "class_name": "Fake", "pid": 1},
            "verification": {"verified": True, "verification_level": "state"},
        }

    def get_foreground(self):
        return {"hwnd": 42, "title": "Test Window", "class_name": "Fake", "pid": 1}

    def list_windows(self, **kwargs):
        return [self.get_foreground()]


class FakeInputController:
    def move_mouse(self, x, y):
        return {"success": True, "stage": "mouse_moved", "verification": {"verified": True, "verification_level": "dispatch"}, "position": {"x": x, "y": y}}

    def click(self, **kwargs):
        return {"success": True, "stage": "mouse_clicked", "verification": {"verified": True, "verification_level": "dispatch"}}

    def type_text(self, text):
        return {"success": True, "stage": "text_typed", "verification": {"verified": True, "verification_level": "dispatch"}, "text_length": len(str(text))}

    def keypress(self, key):
        return {"success": True, "stage": "key_pressed", "verification": {"verified": True, "verification_level": "dispatch"}, "key": key}

    def hotkey(self, keys):
        return {"success": True, "stage": "hotkey_sent", "verification": {"verified": True, "verification_level": "dispatch"}, "keys": list(keys) if not isinstance(keys, str) else [keys]}

    def scroll(self, amount):
        return {"success": True, "stage": "scrolled", "verification": {"verified": True, "verification_level": "dispatch"}, "amount": amount}


class FakeClipboard:
    def set_text(self, text):
        return {"success": True, "stage": "clipboard_set", "verification": {"verified": True, "verification_level": "dispatch"}, "text_length": len(str(text))}

    def get_text(self):
        return {"success": True, "stage": "clipboard_read", "text": "hello", "verification": {"verified": True, "verification_level": "state"}}


class FakeScreen:
    def capture(self, **kwargs):
        return {"success": True, "stage": "screen_captured", "path": "fake.bmp", "verification": {"verified": True, "verification_level": "state"}}


class WindowsUICapabilityTests(unittest.TestCase):
    def make_provider(self):
        return WindowsUICapability(
            window_manager=FakeWindowManager(),
            input_controller=FakeInputController(),
            clipboard_manager=FakeClipboard(),
            screen_observer=FakeScreen(),
        )

    def test_capability_surface_is_generic(self):
        provider = self.make_provider()
        self.assertIn("click", provider.supported_actions())
        self.assertIn("type_text", provider.supported_actions())
        self.assertIn("focus_window", provider.supported_actions())
        self.assertNotIn("open_excel", provider.supported_actions())

    def test_focus_and_type(self):
        provider = self.make_provider()
        focused = provider.execute({"action": "focus_window", "capability": "windows_ui", "target": "Example"})
        self.assertTrue(focused["success"])

        typed = provider.execute({"action": "type_text", "capability": "windows_ui", "target": "hello"})
        self.assertTrue(typed["success"])
        self.assertEqual(typed["text_length"], 5)

    def test_capability_executor_keeps_action_generic(self):
        registry = CapabilityRegistry()
        executor = CapabilityExecutor(registry=registry, validator=ActionValidator(max_steps=5))
        provider = self.make_provider()
        self.assertTrue(executor.register(provider))
        result = executor.execute({
            "action": "click",
            "capability": "windows_ui",
            "target": "",
            "args": {"x": 10, "y": 20},
        })
        self.assertTrue(result["success"])
        self.assertEqual(result["action"]["action"], "click")

    def test_unknown_action_does_not_fall_through_to_legacy(self):
        executor = CapabilityExecutor(registry=CapabilityRegistry())
        result = executor.execute({
            "action": "future_operation",
            "capability": "windows_ui",
            "target": "x",
        })
        self.assertFalse(result["success"])
        self.assertIn("capability", result["stage"] or "")


if __name__ == "__main__":
    unittest.main()
