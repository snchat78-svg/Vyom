"""M10.4 regression tests for the low-resource one-click diagnostic runner."""
from pathlib import Path

from tools import diagnostic_runner


def test_manual_checklist_matches_the_ten_target_device_acceptance_gates():
    ids = [item[0] for item in diagnostic_runner.MANUAL_CHECKS]
    assert ids == [
        "screen_observation",
        "typed_startup_and_exit",
        "hindi_and_hinglish_text",
        "microphone_stt_and_tts",
        "ui_grounding",
        "multi_step_dependencies",
        "postcondition_verification",
        "provider_outage_unknown_answer",
        "memory_consent_and_opt_out",
        "low_memory_stability",
    ]


def test_blank_and_invalid_manual_statuses_remain_not_run():
    answers = iter(["", "", "complete", "", "fail", "a harmless note"])
    evidence = diagnostic_runner._collect_manual_acceptance(lambda _prompt: next(answers))
    assert evidence[0]["status"] == "not_run"
    assert evidence[1]["status"] == "not_run"
    assert evidence[2]["status"] == "fail"
    assert evidence[2]["note"] == "a harmless note"
    assert all(item["user_entered_not_independently_verified"] is True for item in evidence)


def test_manual_notes_are_bounded_and_credential_like_values_are_redacted():
    assert diagnostic_runner._safe_note("api_key=not-a-real-key") == (
        "[redacted: note matched a credential-like pattern]"
    )
    assert len(diagnostic_runner._safe_note("x" * 500)) == 240
    assert "\n" not in diagnostic_runner._safe_note("line one\nline two")


def test_automated_diagnostic_has_no_network_or_audio_capture_claims():
    facts, checks = diagnostic_runner.collect_automated_diagnostics()
    assert "device" in facts
    assert "executable" in facts
    assert checks
    assert all(check["status"] in {"pass", "warn", "fail", "info"} for check in checks)
    microphone = next(check for check in checks if check["id"] == "microphone_device_enumeration")
    assert "recording" in microphone["detail"].lower() or microphone["status"] == "warn"


def test_runner_uses_the_m10_4_checklist_and_explicit_limitations():
    source = Path(diagnostic_runner.__file__).read_text(encoding="utf-8")
    assert "one_click_diagnostics_not_release_acceptance" in source
    assert "No network requests" in source
    assert "user-entered, not independently verified" in source
    assert "M10.4 release acceptance" in source
