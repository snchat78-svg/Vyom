"""Performance and result-contract regressions for application opening."""

from tools.universal_app_launcher import UniversalAppLauncher
from tools.tool_manager import ToolManager


def test_program_files_fallback_is_scoped_to_the_requested_target():
    launcher = UniversalAppLauncher.__new__(UniversalAppLauncher)
    launcher.max_results = 30
    launcher.max_suggestions = 8
    calls = []
    launcher._target_variants = lambda target: [target]
    launcher.find_path_application = lambda _target: None
    launcher.scan_start_menu = lambda: []
    launcher.scan_desktop = lambda: []
    launcher.scan_program_files = lambda target=None: calls.append(target) or []
    launcher.build_database = lambda force=False: []

    launcher.search("calculator")

    assert calls
    assert "calculator" in calls
    # A targetless full Program Files scan is the expensive behavior this
    # regression prevents.
    assert all(value == "calculator" for value in calls)


def test_legacy_open_text_is_not_automatically_promoted_to_success():
    manager = ToolManager.__new__(ToolManager)

    class SelectionState:
        results = []

        @staticmethod
        def has_results():
            return False

    manager.selection_manager = SelectionState()
    manager._verify_open_effect = lambda _target, _before, _raw: (
        False, {}, "foreground_change_not_observed"
    )

    result = manager._open_result_contract(
        "notepad",
        {"hwnd": 100, "title": "Vyom Console"},
        "I could not find 'notepad'.",
    )

    assert result["success"] is False
    assert result["stage"] == "launch_unverified"
    assert result["verification"]["verified"] is False


def test_observed_foreground_change_confirms_open_result():
    manager = ToolManager.__new__(ToolManager)

    class SelectionState:
        results = []

        @staticmethod
        def has_results():
            return False

    manager.selection_manager = SelectionState()
    manager._verify_open_effect = lambda _target, _before, _raw: (
        True, {"hwnd": 200, "title": "Untitled - Notepad"},
        "foreground_window_changed"
    )

    result = manager._open_result_contract(
        "notapaid",
        {"hwnd": 100, "title": "Vyom Console"},
        "Opened successfully: Notepad",
    )

    assert result["success"] is True
    assert result["stage"] == "verified"
    assert result["verification"]["verified"] is True
