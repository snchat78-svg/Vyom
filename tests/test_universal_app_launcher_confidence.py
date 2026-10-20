"""Regression tests for runtime target-match confidence and ambiguity."""

import tools.universal_app_launcher as launcher_module
from tools.universal_app_launcher import UniversalAppLauncher


def _configured_launcher(monkeypatch, quick_candidates, scores, targeted_candidates=None):
    launcher = UniversalAppLauncher()
    monkeypatch.setattr(launcher_module, "find_application", None)
    monkeypatch.setattr(launcher, "_target_variants", lambda _target: ["calc"])
    monkeypatch.setattr(launcher, "find_path_application", lambda _target: None)
    monkeypatch.setattr(launcher, "scan_start_menu", lambda: list(quick_candidates))
    monkeypatch.setattr(launcher, "scan_desktop", lambda: [])
    monkeypatch.setattr(
        launcher, "scan_program_files",
        lambda _target: list(targeted_candidates or []),
    )
    monkeypatch.setattr(launcher, "build_database", lambda force=False: [])
    monkeypatch.setattr(
        launcher, "_match_score",
        lambda _target, name: scores[name],
    )
    return launcher


def test_near_tied_quick_candidate_is_not_dropped_below_strong_cutoff(monkeypatch):
    candidates = [
        {"name": "Calculator", "path": "C:/Apps/Calculator.exe", "type": "path"},
        {"name": "Calculator Beta", "path": "C:/Apps/CalculatorBeta.exe", "type": "path"},
    ]
    launcher = _configured_launcher(
        monkeypatch,
        candidates,
        {"Calculator": 0.92, "Calculator Beta": 0.89},
    )

    result = launcher.search("calc")

    assert [item["name"] for item in result] == [
        "Calculator", "Calculator Beta",
    ]


def test_clear_margin_uses_single_best_runtime_candidate(monkeypatch):
    candidates = [
        {"name": "Calculator", "path": "C:/Apps/Calculator.exe", "type": "path"},
        {"name": "Calculator Beta", "path": "C:/Apps/CalculatorBeta.exe", "type": "path"},
    ]
    launcher = _configured_launcher(
        monkeypatch,
        candidates,
        {"Calculator": 0.94, "Calculator Beta": 0.85},
    )

    result = launcher.search("calc")

    assert [item["name"] for item in result] == ["Calculator"]


def test_near_tied_targeted_program_file_candidate_requires_selection(monkeypatch):
    candidates = [
        {"name": "Calculator", "path": "C:/Program Files/Calculator.exe", "type": "program_files"},
        {"name": "Calculator Beta", "path": "C:/Program Files/CalculatorBeta.exe", "type": "program_files"},
    ]
    launcher = _configured_launcher(
        monkeypatch,
        quick_candidates=[],
        scores={"Calculator": 0.86, "Calculator Beta": 0.81},
        targeted_candidates=candidates,
    )

    result = launcher.search("calc")

    assert [item["name"] for item in result] == [
        "Calculator", "Calculator Beta",
    ]
