import subprocess
from types import SimpleNamespace

from windows_agent.process_manager import ProcessManager


def _tasklist(*rows):
    return "\r\n".join(
        '"' + '","'.join(str(value) for value in row) + '"'
        for row in rows
    )


def test_close_app_uses_exact_image_name_and_graceful_pid(monkeypatch):
    calls = []
    outputs = [
        _tasklist(("CalculatorApp.exe", "1234", "Console", "1", "10,000 K")),
        "",
    ]

    def fake_run(command, **kwargs):
        calls.append(list(command))
        if command[0] == "tasklist":
            return SimpleNamespace(returncode=0, stdout=outputs.pop(0), stderr="")
        return SimpleNamespace(returncode=0, stdout="SUCCESS", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = ProcessManager().close_app("CalculatorApp")

    assert "process exit was verified" in result
    taskkill = next(call for call in calls if call[0] == "taskkill")
    assert taskkill == ["taskkill", "/PID", "1234", "/T"]
    assert "/F" not in taskkill
    assert "/IM" not in taskkill


def test_close_app_does_not_use_substring_process_matches(monkeypatch):
    calls = []

    def fake_run(command, **kwargs):
        calls.append(list(command))
        return SimpleNamespace(
            returncode=0,
            stdout=_tasklist(("Calculator.exe", "1234", "Console", "1", "10,000 K")),
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = ProcessManager().close_app("calc")

    assert "No exact running process" in result
    assert not any(call[0] == "taskkill" for call in calls)


def test_close_app_does_not_close_multiple_same_name_instances(monkeypatch):
    calls = []

    def fake_run(command, **kwargs):
        calls.append(list(command))
        return SimpleNamespace(
            returncode=0,
            stdout=_tasklist(
                ("notepad.exe", "100", "Console", "1", "10,000 K"),
                ("notepad.exe", "200", "Console", "1", "10,000 K"),
            ),
            stderr="",
        )

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = ProcessManager().close_app("notepad")

    assert "Multiple" in result
    assert not any(call[0] == "taskkill" for call in calls)


def test_close_app_does_not_claim_closed_when_pid_remains(monkeypatch):
    calls = []

    def fake_run(command, **kwargs):
        calls.append(list(command))
        if command[0] == "tasklist":
            return SimpleNamespace(
                returncode=0,
                stdout=_tasklist(("notepad.exe", "100", "Console", "1", "10,000 K")),
                stderr="",
            )
        return SimpleNamespace(returncode=0, stdout="SUCCESS", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)
    result = ProcessManager().close_app("notepad")

    assert "still running" in result
    assert "did not force-terminate" in result
