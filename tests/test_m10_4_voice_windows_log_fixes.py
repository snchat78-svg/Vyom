"""Regression tests for noisy voice targets, known folders and WM_CLOSE safety."""

import os
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from ctypes import wintypes

from tools.phonetic_matcher import score_candidate
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


class GenericVoiceTargetTests(unittest.TestCase):
    def test_hinglish_transcriptions_match_discovered_application_names(self):
        self.assertGreaterEqual(score_candidate("eksel", "Excel"), 0.80)
        self.assertGreaterEqual(score_candidate("gugal krom", "Google Chrome"), 0.80)
        self.assertGreaterEqual(score_candidate("kailakuletar", "Calculator"), 0.80)
        self.assertGreaterEqual(score_candidate("krom", "Chrome"), 0.80)
        self.assertGreaterEqual(score_candidate("eksel", "Microsoft Excel 2016"), 0.80)
        self.assertLess(score_candidate("gugal krom", "Microsoft Excel 2016"), 0.80)


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
        ticks = iter([0.0, 1.0, 3.0])
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
