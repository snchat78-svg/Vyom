"""Regression tests for noisy voice targets, known folders and WM_CLOSE safety."""

import os
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from ctypes import wintypes

from tools.phonetic_matcher import score_candidate
from ai_core.semantic_brain import LocalSemanticBrain
import command_engine.executor as executor_module
from tools.universal_resolver import UniversalResolver
from tools.tool_manager import ToolManager
import tools.tool_manager as tool_manager_module
from windows_agent.ui_automation import WindowsUICapability
import windows_agent.window_manager as window_manager_module


class _FakeWin32Call:
    def __init__(self, result=1):
        self.result = result
        self.argtypes = None
        self.restype = None

    def __call__(self, *args):
        return self.result


class ScreenUnderstandingIntentTests(unittest.TestCase):
    def test_hinglish_screen_request_routes_to_read_only_screen_capability(self):
        for phrase in ("screen samjhao", "screen par kya hai", "स्क्रीन समझाओ"):
            with self.subTest(phrase=phrase):
                result = LocalSemanticBrain().reason(phrase, context={})
                self.assertEqual(result["route"], "capability")
                self.assertEqual(result["plan"][0]["action"], "analyze_screen")
                self.assertEqual(result["plan"][0]["capability"], "screen_understanding")
                self.assertFalse(result["meaning"]["requires_clarification"])

    def test_screen_analysis_capability_never_becomes_a_computer_action(self):
        result = LocalSemanticBrain().reason("what is on my screen", context={})
        step = result["plan"][0]
        self.assertEqual(step["action"], "analyze_screen")
        self.assertEqual(step["capability"], "screen_understanding")
        self.assertEqual(step["args"]["question"], "what is on my screen")


class CurrentForegroundObservationTests(unittest.TestCase):
    def test_close_current_prefers_direct_win32_foreground_over_world_state(self):
        original_manager = executor_module.tool_manager
        original_agent = executor_module.autonomous_agent
        try:
            manager = SimpleNamespace(
                _foreground_snapshot=lambda: {"hwnd": 811, "title": "Notepad"}
            )
            agent = SimpleNamespace(
                world_state=SimpleNamespace(
                    snapshot=lambda *args, **kwargs: (_ for _ in ()).throw(
                        AssertionError("UIA/WorldState must not override live Win32 HWND")
                    )
                ),
                mission_runtime=SimpleNamespace(snapshot=lambda: {}),
                context=SimpleNamespace(snapshot=lambda: {}),
            )
            executor_module.tool_manager = manager
            executor_module.autonomous_agent = agent

            window, source = executor_module._observed_foreground_window()

            self.assertEqual(source, "win32_foreground")
            self.assertEqual(window, {"hwnd": 811, "title": "Notepad"})
        finally:
            executor_module.tool_manager = original_manager
            executor_module.autonomous_agent = original_agent

    def test_close_current_falls_back_to_coherent_world_state_when_win32_missing(self):
        original_manager = executor_module.tool_manager
        original_agent = executor_module.autonomous_agent
        try:
            manager = SimpleNamespace(_foreground_snapshot=lambda: {})
            agent = SimpleNamespace(
                world_state=SimpleNamespace(snapshot=lambda *args, **kwargs: {
                    "current_window": {"hwnd": 812, "title": "Google Chrome"},
                    "ui": {"available": True, "coherent": True},
                }),
                mission_runtime=SimpleNamespace(snapshot=lambda: {}),
                context=SimpleNamespace(snapshot=lambda: {}),
            )
            executor_module.tool_manager = manager
            executor_module.autonomous_agent = agent

            window, source = executor_module._observed_foreground_window()

            self.assertEqual(source, "world_state_ui")
            self.assertEqual(window, {"hwnd": 812, "title": "Google Chrome"})
        finally:
            executor_module.tool_manager = original_manager
            executor_module.autonomous_agent = original_agent

    def test_close_current_refuses_a_remembered_app_without_live_hwnd(self):
        original_manager = executor_module.tool_manager
        original_agent = executor_module.autonomous_agent
        try:
            manager = SimpleNamespace(_foreground_snapshot=lambda: {})
            agent = SimpleNamespace(
                world_state=SimpleNamespace(snapshot=lambda *args, **kwargs: {
                    "current_window": {},
                    "ui": {"available": False},
                }),
                mission_runtime=SimpleNamespace(snapshot=lambda: {}),
                context=SimpleNamespace(snapshot=lambda: {"current_app": "Notepad"}),
            )
            executor_module.tool_manager = manager
            executor_module.autonomous_agent = agent

            window, source = executor_module._observed_foreground_window()

            self.assertEqual(window, {})
            self.assertEqual(source, "foreground_unavailable")
        finally:
            executor_module.tool_manager = original_manager
            executor_module.autonomous_agent = original_agent


class GenericVoiceTargetTests(unittest.TestCase):
    def test_hinglish_transcriptions_match_discovered_application_names(self):
        self.assertGreaterEqual(score_candidate("eksel", "Excel"), 0.80)
        self.assertGreaterEqual(score_candidate("gugal krom", "Google Chrome"), 0.80)
        self.assertGreaterEqual(score_candidate("kailakuletar", "Calculator"), 0.80)
        self.assertGreaterEqual(score_candidate("krom", "Chrome"), 0.80)
        self.assertGreaterEqual(score_candidate("eksel", "Microsoft Excel 2016"), 0.80)
        self.assertLess(score_candidate("gugal krom", "Microsoft Excel 2016"), 0.80)
        self.assertGreaterEqual(score_candidate("gugal krom", "Chrome"), 0.90)
        self.assertFalse(ToolManager._same_runtime_target("Notepad", "Notepad++"))


class KnownUserFolderTests(unittest.TestCase):
    @staticmethod
    def _isolated_resolver(common_paths):
        resolver = UniversalResolver()
        resolver.common_paths = common_paths
        # Never let the CI host's own Start Menu applications or desktop
        # shortcuts influence a test about personal-folder root resolution.
        resolver.start_menu_paths = []
        resolver.desktop_paths = []
        resolver.find_in_path = lambda _target: None
        resolver.search_registry_app_paths = lambda _target: []
        resolver.search_start_menu = lambda _target: []
        resolver.search_desktop = lambda _target: []
        resolver._fuzzy_search_known_locations = lambda _target: []
        return resolver

    def test_photo_alias_resolves_existing_pictures_root(self):
        with tempfile.TemporaryDirectory() as root:
            pictures = os.path.join(root, "Pictures")
            os.makedirs(pictures)
            resolver = self._isolated_resolver([pictures])

            self.assertEqual(resolver.find("photos"), [pictures])
            self.assertEqual(
                resolver.find_file_or_folder("my pictures folder"),
                [pictures],
            )

    def test_known_folder_alias_does_not_return_missing_directory(self):
        with tempfile.TemporaryDirectory() as root:
            missing = os.path.join(root, "Pictures")
            resolver = self._isolated_resolver([missing])

            self.assertEqual(resolver.find("photos"), [])
            self.assertEqual(resolver.find_file_or_folder("pictures"), [])

    def test_unrelated_custom_folder_is_not_guessed_as_pictures(self):
        with tempfile.TemporaryDirectory() as root:
            custom = os.path.join(root, "Family Archive")
            os.makedirs(custom)
            resolver = self._isolated_resolver([custom])

            self.assertEqual(resolver.find("photos"), [])


class ForegroundCloseResolutionTests(unittest.TestCase):
    def test_noisy_notepad_transcript_resolves_live_foreground_hwnd(self):
        manager = ToolManager.__new__(ToolManager)
        manager._foreground_snapshot = lambda: {
            "hwnd": 501,
            "title": "Notepad",
        }

        result = manager._resolve_foreground_for_close("notapaid", {})

        self.assertTrue(result["success"])
        self.assertEqual(result["window"]["hwnd"], 501)
        self.assertEqual(result["window"]["title"], "Notepad")
        self.assertEqual(result["window"]["source"], "win32_foreground")

    def test_close_resolution_does_not_choose_an_unrelated_foreground_window(self):
        manager = ToolManager.__new__(ToolManager)
        manager._foreground_snapshot = lambda: {
            "hwnd": 502,
            "title": "Calculator",
        }

        result = manager._resolve_foreground_for_close("notapaid", {})

        self.assertFalse(result["success"])
        self.assertEqual(result["stage"], "foreground_target_not_matched")
        self.assertEqual(result["observed_title"], "Calculator")


class OpenWindowVerificationTests(unittest.TestCase):
    @staticmethod
    def _manager(title):
        manager = ToolManager.__new__(ToolManager)
        manager._foreground_snapshot = lambda: {
            "hwnd": 200,
            "title": title,
        }
        return manager

    def test_excel_launch_verification_matches_runtime_title_token(self):
        manager = self._manager("Book1 - Microsoft Excel 2016")
        ticks = iter([0.0, 0.0, 1.0, 1.0, 9.0])
        with patch.object(tool_manager_module.time, "monotonic", side_effect=lambda: next(ticks)):
            with patch.object(tool_manager_module.time, "sleep", return_value=None):
                verified, window, method = manager._verify_open_effect(
                    "eksel",
                    {"hwnd": 100, "title": "Vyom Console"},
                    {"success": True, "results": [{"name": "Microsoft Excel 2016"}]},
                )

        self.assertTrue(verified)
        self.assertEqual(window["hwnd"], 200)
        self.assertEqual(method, "foreground_title_match")

    def test_chrome_short_caption_verifies_spoken_multiword_target(self):
        manager = self._manager("Shambhulal - Chrome")
        ticks = iter([0.0, 0.0, 1.0, 1.0, 9.0])
        with patch.object(tool_manager_module.time, "monotonic", side_effect=lambda: next(ticks)):
            with patch.object(tool_manager_module.time, "sleep", return_value=None):
                verified, window, method = manager._verify_open_effect(
                    "gugal krom",
                    {"hwnd": 100, "title": "Vyom Console"},
                    {"success": True, "results": [{"name": "Google Chrome"}]},
                )

        self.assertTrue(verified)
        self.assertEqual(window["title"], "Shambhulal - Chrome")
        self.assertEqual(method, "foreground_title_match")


    def test_unrelated_foreground_window_change_does_not_verify_app_launch(self):
        manager = self._manager("Unrelated Window")
        ticks = iter([0.0, 1.0, 3.0])
        with patch.object(tool_manager_module.time, "monotonic", side_effect=lambda: next(ticks)):
            with patch.object(tool_manager_module.time, "sleep", return_value=None):
                verified, window, method = manager._verify_open_effect(
                    "eksel",
                    {"hwnd": 100, "title": "Vyom Console"},
                    {"success": True, "results": [{"name": "Microsoft Excel 2016"}]},
                )

        self.assertFalse(verified)
        self.assertEqual(window["hwnd"], 200)
        self.assertEqual(method, "foreground_changed_without_target_match")


class WindowManagerSignatureTests(unittest.TestCase):
    def test_post_message_uses_pointer_sized_win32_parameters(self):
        user32 = SimpleNamespace(
            GetForegroundWindow=_FakeWin32Call(),
            IsWindow=_FakeWin32Call(),
            ShowWindow=_FakeWin32Call(),
            BringWindowToTop=_FakeWin32Call(),
            SetForegroundWindow=_FakeWin32Call(),
            PostMessageW=_FakeWin32Call(),
        )
        with patch.object(window_manager_module.os, "name", "nt"):
            with patch.object(
                window_manager_module.ctypes,
                "windll",
                SimpleNamespace(user32=user32),
                create=True,
            ):
                manager = window_manager_module.WindowManager()

        self.assertTrue(manager.is_available())
        self.assertEqual(
            user32.PostMessageW.argtypes,
            [
                wintypes.HWND,
                wintypes.UINT,
                wintypes.WPARAM,
                wintypes.LPARAM,
            ],
        )
        self.assertEqual(user32.PostMessageW.restype, wintypes.BOOL)


class _FakeWindowManagerForClose:
    def __init__(self, accepts_message):
        self.closed = False
        self.accepts_message = bool(accepts_message)
        self.posted_arguments = None
        self._user32 = SimpleNamespace(PostMessageW=self._post_message)

    def _post_message(self, hwnd, message, wparam, lparam):
        self.posted_arguments = (hwnd, message, wparam, lparam)
        if self.accepts_message:
            self.closed = True
        return self.accepts_message

    def find(self, hwnd=None, **_kwargs):
        if self.closed:
            return []
        return [{"hwnd": hwnd or 77, "title": "Google Chrome"}]


class ObservedWindowCloseTests(unittest.TestCase):
    @staticmethod
    def _provider(manager):
        provider = WindowsUICapability.__new__(WindowsUICapability)
        provider.window_manager = manager
        return provider

    def test_close_uses_observed_window_handle_and_verifies_disappearance(self):
        manager = _FakeWindowManagerForClose(accepts_message=True)
        result = self._provider(manager)._close_application({
            "action": "close_application",
            "target": "gugal krom",
            "args": {"hwnd": 77},
        })

        self.assertTrue(result["success"])
        self.assertEqual(result["stage"], "verified")
        self.assertEqual(manager.posted_arguments, (77, 0x0010, 0, 0))
        self.assertTrue(manager.closed)

    def test_rejected_close_message_is_not_reported_as_success(self):
        manager = _FakeWindowManagerForClose(accepts_message=False)
        result = self._provider(manager)._close_application({
            "action": "close_application",
            "target": "gugal krom",
            "args": {"hwnd": 77},
        })

        self.assertFalse(result["success"])
        self.assertEqual(result["stage"], "close_dispatch_failed")
        self.assertFalse(manager.closed)


if __name__ == "__main__":
    unittest.main()
