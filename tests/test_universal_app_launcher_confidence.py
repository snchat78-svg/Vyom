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

def _mock_appsfolder_items(monkeypatch, stdout):
    class FakeProcess:
        returncode = 0

        def communicate(self, timeout=None):
            return stdout, ""

    monkeypatch.setattr(
        launcher_module.subprocess,
        "Popen",
        lambda *args, **kwargs: FakeProcess(),
    )


def test_direct_appsfolder_duplicate_names_require_explicit_selection(monkeypatch):
    stdout = (
        "MATCH\tDuplicate App\tshell:AppsFolder\\Publisher.AppOne!Main\n"
        "MATCH\tDuplicate App\tshell:AppsFolder\\Publisher.AppTwo!Main\n"
    )
    _mock_appsfolder_items(monkeypatch, stdout)

    launcher = UniversalAppLauncher()
    monkeypatch.setattr(launcher, "is_windows", lambda: True)
    monkeypatch.setattr(launcher, "search", lambda _target, force_refresh=False: [])
    monkeypatch.setattr(launcher, "_target_variants", lambda target: [target])
    launches = []
    monkeypatch.setattr(
        launcher,
        "open_by_aumid",
        lambda app_id: launches.append(app_id) or True,
    )
    monkeypatch.setattr(
        launcher,
        "find_similar",
        lambda _target: (_ for _ in ()).throw(AssertionError("must ask before suggestions")),
    )

    result = launcher.open("Duplicate App")

    assert result["success"] is False
    assert len(result["results"]) == 2
    assert result["results"][0]["type"].startswith("AppsFolder:")
    assert result["results"][1]["type"].startswith("AppsFolder:")
    assert "1. Duplicate App [AppsFolder:" in result["message"]
    assert "2. Duplicate App [AppsFolder:" in result["message"]
    assert "Please select a number." in result["message"]
    assert launches == []


def test_direct_appsfolder_unique_name_still_launches(monkeypatch):
    stdout = "MATCH\tUnique App\tshell:AppsFolder\\Publisher.UniqueApp!Main\n"
    _mock_appsfolder_items(monkeypatch, stdout)

    launcher = UniversalAppLauncher()
    monkeypatch.setattr(launcher, "is_windows", lambda: True)
    monkeypatch.setattr(launcher, "search", lambda _target, force_refresh=False: [])
    monkeypatch.setattr(launcher, "_target_variants", lambda target: [target])
    launches = []
    monkeypatch.setattr(
        launcher,
        "open_by_aumid",
        lambda app_id: launches.append(app_id) or True,
    )

    result = launcher.open("Unique App")

    assert result["success"] is True
    assert launches == ["Publisher.UniqueApp!Main"]

