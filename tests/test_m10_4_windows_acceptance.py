"""M10.4 static contract checks for target-device evidence collection.

These checks do not claim that a real Windows device, microphone or UI was tested.
"""
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (ROOT / "tools" / "vyom_windows_acceptance.ps1").read_text(encoding="utf-8")


def test_m10_4_keeps_preflight_as_default_and_manual_collection_opt_in():
    assert '[switch]$AttemptLaunchSmokeTest' in SCRIPT
    assert '[switch]$CollectManualEvidence' in SCRIPT
    assert 'scope = "preflight_only_not_device_acceptance"' not in SCRIPT  # scope is now explicitly selected by mode
    assert "preflight_only_not_device_acceptance" in SCRIPT
    assert "target_device_manual_evidence_user_entered_not_independently_verified" in SCRIPT


def test_m10_4_manual_evidence_cannot_be_collected_as_github_device_evidence():
    assert '$environmentKind -eq "github_actions_runner"' in SCRIPT
    assert "Manual evidence collection is disabled on GitHub Actions" in SCRIPT
    assert "target_device_blocked_unsupported_os" in SCRIPT
    assert "target_device_blocked_missing_exe" in SCRIPT


def test_m10_4_manual_results_are_explicit_and_invalid_entries_stay_not_run():
    for status in ('"pass"', '"fail"', '"block"', '"not_run"'):
        assert status in SCRIPT
    assert "Unrecognized status; leaving this test not_run." in SCRIPT
    assert "Manual evidence is user-entered and is not independently verified" not in SCRIPT
    assert "not independently verified" in SCRIPT


def test_m10_4_evidence_notes_are_bounded_and_credential_like_text_is_redacted():
    assert "$enteredNote.Length -gt 240" in SCRIPT
    assert "[redacted: note matched a credential-like pattern]" in SCRIPT
    assert "Do not enter passwords, API keys, private transcripts, or personal file contents." in SCRIPT


def test_m10_4_workflow_builds_and_uploads_single_target_device_package():
    workflow = (ROOT / ".github" / "workflows" / "vyom.yml").read_text(encoding="utf-8")
    package_readme = (
        ROOT / "docs" / "VYOM_M10_4_TARGET_DEVICE_PACKAGE_README.txt"
    ).read_text(encoding="utf-8")

    assert "Prepare M10.4 target-device package" in workflow
    assert "Vyom_M10_4_Target_Device_Package.zip" in workflow
    assert "name: Vyom_M10_4_Target_Device_Package" in workflow
    assert 'Copy-Item -LiteralPath "dist/Vyom.exe"' in workflow
    assert 'Copy-Item -LiteralPath "tools/vyom_windows_acceptance.ps1"' in workflow
    assert 'Copy-Item -LiteralPath "docs/VYOM_M10_4_WINDOWS_ACCEPTANCE.md"' in workflow
    assert "README_FIRST.txt" in workflow
    assert "No Python installation is required for the EXE or preflight script." in package_readme
    assert "Windows 8.0/version 6.2 is unsupported" in package_readme
    assert "-CollectManualEvidence" in package_readme
    assert "not_run" in package_readme
    assert "M10_4_preflight.json" in package_readme
