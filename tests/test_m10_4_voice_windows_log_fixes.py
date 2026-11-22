"""Regressions for the 2026-11-22 Windows voice-log investigation."""

import os
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from ctypes import wintypes

from tools.phonetic_matcher import score_candidate
from tools.universal_resolver import UniversalResolver
from windows_agent.ui_automation import WindowsUICapability
import windows_agent.window_manager as window_manager_module


class GenericVoiceTargetTests(unittest.TestCase):
    def test_common_hinglish_app_pronunciations_match_runtime_names(self):
        self.assertGreaterEqual(score_candidate("eksel", "Excel"), 0.80)
        self.assertGreaterEqual(score_candidate("gugal krom", "Google Chrome"), 0.80)
        self.assertGreaterEqual(score_candidate("kailakuletar", "Calculator"), 0.80)

    def test_chrome_does_not_require_an_application_alias(self):
        # The generic sound matcher should compare speech with a discovered
        # title/name; it must not depend on a hard-coded Chrome alias.
        self.assertGreaterEqual(score_candidate("krom", "Chrome"), 0.80)


class KnownUserFolderTests(unittest.TestCase):
    def test_photos_alias_resolves_existing_pictures_root(self):
        with tempfile.TemporaryDirectory() as root:
            pictures = os.path.join(root, "Pictures")
            os.makedirs(pictures)
            resolver = UniversalResolver()
            resolver.common_paths = [pictures]

            self.assertEqual(resolver.find("photos"), [pictures])
            self.assertEqual(
                resolver.find_file_or_folder("my pictures folder"),
                [pictures],
            )

    def test_standard_folder_alias_does_not_return_a_missing_directory(self):
        with tempfile.TemporaryDirectory() as root:
            missing = os.path.join(root, "Pictures")
            resolver = UniversalResolver()
            resolver.common_paths = [missing]

            self.assertEqual(resolver.find("photos"), [])
            self.assertEqual(resolver.find_file_or_folder("pictures"), [])

    def test_custom_folder_is_not_guessed_as_a_standard_photos_folder(self):
        with tempfile.TemporaryDirectory() as root:
            custom = os.path.join(root, "Family Archive")
            os.makedirs(custom)
            resolver = UniversalResolver()
            resolver.common_paths = [custom]

            self.assertEqual(resolver.find("photos"), [])


class _FakeWin32Call:
    def __init__(self, result=1):
        self.result = result
        self.argtypes = None
        self.restype = None

    def __call__(self, *args):
        return self.result


class WindowManagerSignatureTests(unittest.TestCase):
    def test_post_message_uses_pointer_safe_win32_types(self):
        user32 = SimpleNamespace(
            GetForegroundWindow=_FakeWin32Call(),
            IsWindow=_FakeWin32Call(),
            ShowWindow=_FakeWin32Call(),
            BringWindowToTop=_FakeWin32Call(),
            SetForegroundWindow=_FakeWin32Call(),
            PostMessageW=_FakeWin32Call(),
        )
        fake_windll = SimpleNamespace(user32=user32)

        with patch.object(window_manager_module.os, "name", "nt"):
            with patch.object(
                window_manager_module.ctypes,
                "windll",
                fake_windll,
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
        self.post_message = _FakeWin32Call(result=int(accepts_message))
        self._user32 = SimpleNamespace(PostMessageW=self._post_message)

    def _post_message(self, hwnd, message, wparam, lparam):
        self.post_message(hwnd, message, wparam, lparam)
        if self.post_message.result:
            self.closed = True
        return self.post_message.result

    def find(self, hwnd=None, **_kwargs):
        if self.closed:
            return []
        return [{"hwnd": hwnd or 77, "title": "Google Chrome"}]


class ObservedWindowCloseTests(unittest.TestCase):
    def _provider(self, manager):
        provider = WindowsUICapability.__new__(WindowsUICapability)
        provider.window_manager = manager
        return provider

    def test_close_uses_observed_hwnd_and_verifies_window_disappears(self):
        manager = _FakeWindowManagerForClose(accepts_message=True)
        result = self._provider(manager)._close_application({
            "action": "close_application",
            "target": "gugal krom",
            "args": {"hwnd": 77},
        })

        self.assertTrue(result["success"])
        self.assertEqual(result["stage"], "verified")
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
