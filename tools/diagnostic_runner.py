"""Low-resource, local-only M10.4 diagnostics for Vyom.

Read-only environment checks plus user-entered acceptance observations.
No app launching, clicking, audio recording, setting changes, package installs,
model downloads, or network requests are performed.
"""
from __future__ import annotations

import ctypes
import hashlib
import importlib.util
import json
import os
import platform
import re
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Optional


MANUAL_CHECKS = (
    ("screen_observation", "Read-only screen/UI observation",
     "Verify Vyom identifies the active window and visible controls without clicking."),
    ("typed_startup_and_exit", "Typed startup and exit",
     "Launch Vyom normally, send a harmless typed greeting, then exit gracefully."),
    ("hindi_and_hinglish_text", "Hindi and Hinglish text",
     "Try Hindi, Roman Hindi, and Hinglish commands/replies; note incorrect meaning."),
    ("microphone_stt_and_tts", "Microphone, STT, and audible TTS",
     "Speak a short command and confirm both recognition and audible speech output."),
    ("ui_grounding", "UI target grounding",
     "Check that ambiguous targets are clarified and the correct window/control is identified."),
    ("multi_step_dependencies", "Multi-step dependencies",
     "Try a harmless two-step task; dependent work must wait for its prerequisite."),
    ("postcondition_verification", "Postcondition verification",
     "Check that Vyom reports success only after the expected visible change is observed."),
    ("provider_outage_unknown_answer", "Offline factual answer",
     "Only when safe, test an unavailable-network factual lookup; Vyom must say unknown, not guess."),
    ("memory_consent_and_opt_out", "Memory consent and opt-out",
     "Check that consent starts off and opting out immediately blocks memory use."),
    ("low_memory_stability", "Low-memory stability",
     "Observe responsiveness and crashes during normal use on this actual PC."),
)

_VALID_STATUSES = {"pass", "fail", "block", "not_run"}
_SECRET_PATTERNS = (
    re.compile(r"(?i)(password\s*[:=]|api[_ -]?key\s*[:=]|bearer\s+[A-Za-z0-9._-]{12,})"),
    re.compile(r"-----BEGIN .*PRIVATE KEY-----"),
    re.compile(r"(?i)\bsk-[A-Za-z0-9]{16,}\b"),
)


def _safe_note(value: str) -> str:
    note = " ".join(str(value or "").replace("\r", " ").replace("\n", " ").split())
    if any(pattern.search(note) for pattern in _SECRET_PATTERNS):
        return "[redacted: note matched a credential-like pattern]"
    return note[:240]


def _module_available(module_name: str) -> bool:
    try:
        return importlib.util.find_spec(module_name) is not None
    except (ImportError, ModuleNotFoundError, ValueError, AttributeError):
        return False


def _physical_memory() -> dict:
    if os.name == "nt":
        class MEMORYSTATUSEX(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong), ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong), ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong), ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong), ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]
        try:
            status = MEMORYSTATUSEX()
            status.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
                return {
                    "total_mb": int(status.ullTotalPhys // (1024 * 1024)),
                    "available_mb": int(status.ullAvailPhys // (1024 * 1024)),
                    "load_percent": int(status.dwMemoryLoad),
                }
        except Exception:
            pass
    try:
        page_size = int(os.sysconf("SC_PAGE_SIZE"))
        total_pages = int(os.sysconf("SC_PHYS_PAGES"))
        available_pages = int(os.sysconf("SC_AVPHYS_PAGES"))
        return {
            "total_mb": total_pages * page_size // (1024 * 1024),
            "available_mb": available_pages * page_size // (1024 * 1024),
            "load_percent": None,
        }
    except (AttributeError, OSError, ValueError):
        return {"total_mb": None, "available_mb": None, "load_percent": None}


def _sapi_voice_count() -> Optional[int]:
    if os.name != "nt":
        return None
    try:
        import winreg
        key_path = r"SOFTWARE\Microsoft\Speech\Voices\Tokens"
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as key:
            count = 0
            while True:
                try:
                    winreg.EnumKey(key, count)
                    count += 1
                except OSError:
                    break
            return count
    except (ImportError, OSError):
        return 0


def _microphone_device_count() -> tuple[Optional[int], Optional[str]]:
    if not _module_available("speech_recognition") or not _module_available("pyaudio"):
        return None, "SpeechRecognition or PyAudio is not installed."
    try:
        import speech_recognition as sr
        names = sr.Microphone.list_microphone_names()
        return len(names), None
    except Exception as error:
        return None, type(error).__name__


def _system_facts() -> dict:
    memory = _physical_memory()
    win_version = None
    if os.name == "nt":
        try:
            info = sys.getwindowsversion()
            win_version = f"{info.major}.{info.minor}.{info.build}"
        except Exception:
            win_version = platform.version()
    return {
        "os_name": platform.system(),
        "os_release": platform.release(),
        "os_version": win_version or platform.version(),
        "architecture": platform.machine(),
        "python_version": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "is_frozen_executable": bool(getattr(sys, "frozen", False)),
        "physical_memory_mb": memory,
    }


def collect_automated_diagnostics() -> tuple[dict, list[dict]]:
    device = _system_facts()
    checks = []

    def add(check_id: str, status: str, detail: str) -> None:
        checks.append({"id": check_id, "status": status, "detail": detail})

    add("runtime", "pass",
        f"{device['python_implementation']} {device['python_version']} runtime is active.")

    if os.name == "nt":
        try:
            version = sys.getwindowsversion()
            supported = (version.major, version.minor) >= (6, 3)
            add("windows_compatibility", "pass" if supported else "fail",
                "Windows 8.1/version 6.3 or newer is required by the current Python 3.11 package."
                if supported else "This Windows version is below the current Python 3.11 package baseline.")
        except Exception:
            add("windows_compatibility", "warn", "Windows version could not be confirmed.")
    else:
        add("windows_compatibility", "info",
            "Not running on Windows; target-PC compatibility was not tested.")

    memory = device["physical_memory_mb"]
    if memory.get("total_mb") is None:
        add("physical_memory", "warn", "Physical RAM could not be read.")
    else:
        add("physical_memory", "info",
            f"RAM total: {memory['total_mb']} MB; available now: {memory['available_mb']} MB. "
            "No product pass/fail RAM threshold is defined by this diagnostic.")

    core_modules = (
        "ai_core.main", "ai_core.semantic_brain", "ai_core.autonomous_agent",
        "command_engine.executor", "tools.tool_manager", "windows_agent.ui_state_observer",
        "windows_agent.ui_verifier", "voice.voice_controller",
    )
    missing_core = [name for name in core_modules if not _module_available(name)]
    add("core_modules", "fail" if missing_core else "pass",
        "Missing: " + ", ".join(missing_core) if missing_core
        else "Core reasoning, action, UI, and voice module paths are present.")

    optional_modules = {
        "speech_recognition": "SpeechRecognition",
        "pyaudio": "PyAudio microphone backend",
        "pyttsx3": "pyttsx3 text-to-speech package",
        "pywinauto": "Windows UI automation package",
    }
    missing_optional = [
        label for module, label in optional_modules.items() if not _module_available(module)
    ]
    add("optional_dependencies", "warn" if missing_optional else "pass",
        "Not found: " + ", ".join(missing_optional) if missing_optional
        else "Voice and Windows UI automation dependency paths are present.")

    mic_count, mic_error = _microphone_device_count()
    if mic_count is None:
        add("microphone_device_enumeration", "warn",
            mic_error or "Microphone devices could not be enumerated.")
    elif mic_count == 0:
        add("microphone_device_enumeration", "warn",
            "No microphone devices were listed; no audio was recorded.")
    else:
        add("microphone_device_enumeration", "pass",
            f"{mic_count} microphone device(s) listed; recording and recognition quality were not tested.")

    voice_count = _sapi_voice_count()
    if voice_count is None:
        add("windows_sapi_voices", "info", "SAPI voice registry check applies only to Windows.")
    elif voice_count == 0:
        add("windows_sapi_voices", "warn", "No registered Windows SAPI voices were found.")
    else:
        add("windows_sapi_voices", "pass",
            f"{voice_count} Windows SAPI voice(s) registered; audible playback and Hindi-language support were not tested.")

    allow_paid = os.environ.get("VYOM_ALLOW_PAID_API", "false").strip().lower()
    if allow_paid in {"1", "true", "yes", "on"}:
        add("paid_api_override", "warn",
            "A paid-provider override is enabled in this process environment.")
    else:
        add("paid_api_override", "pass",
            "No paid-provider override is enabled in this process environment.")

    executable = Path(sys.executable)
    executable_info = {"file_name": executable.name, "sha256": None}
    try:
        digest = hashlib.sha256()
        with executable.open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
        executable_info["sha256"] = digest.hexdigest()
    except OSError:
        executable_info["hash_status"] = "unavailable"

    return {"device": device, "executable": executable_info}, checks


def _collect_manual_acceptance(input_func: Callable[[str], str]) -> list[dict]:
    evidence = []
    for check_id, title, instruction in MANUAL_CHECKS:
        try:
            status_text = input_func(
                f"\n[{check_id}] {title}\n{instruction}\n"
                "Status [pass/fail/block/not_run; Enter=not_run]: "
            )
        except (EOFError, KeyboardInterrupt):
            status_text = ""
        status = str(status_text or "").strip().lower()
        if status not in _VALID_STATUSES:
            status = "not_run"
        try:
            note_text = input_func("Short non-sensitive observation (optional): ")
        except (EOFError, KeyboardInterrupt):
            note_text = ""
        evidence.append({
            "id": check_id,
            "status": status,
            "note": _safe_note(note_text),
            "user_entered_not_independently_verified": True,
        })
    return evidence


def _report_directory() -> Optional[Path]:
    candidates = [
        Path.home() / "Documents" / "VyomDiagnostics",
        Path(tempfile.gettempdir()) / "VyomDiagnostics",
    ]
    for candidate in candidates:
        try:
            candidate.mkdir(parents=True, exist_ok=True)
            probe = candidate / ".vyom_diagnostic_write_test"
            probe.write_text("ok", encoding="utf-8")
            probe.unlink()
            return candidate
        except OSError:
            continue
    return None


def run_diagnostics(
    input_func: Optional[Callable[[str], str]] = None,
    output_func: Callable[[str], None] = print,
) -> dict:
    input_func = input_func or input
    output_func("\n===================================")
    output_func(" VYOM — ONE-CLICK DIAGNOSTICS")
    output_func("===================================")
    output_func("Read-only automated checks; no network, app launching, clicking, or audio recording.")

    facts, checks = collect_automated_diagnostics()
    for check in checks:
        output_func(f"[{check['status'].upper()}] {check['id']}: {check['detail']}")

    output_func("\nNow record only the manual checks you actually performed.")
    output_func("Use pass, fail, block, or not_run. Blank/invalid answers remain not_run.")
    manual = _collect_manual_acceptance(input_func)
    statuses = [item["status"] for item in manual]
    counts = {status: statuses.count(status) for status in sorted(_VALID_STATUSES)}

    report = {
        "schema_version": 1,
        "phase_id": "M10.4",
        "report_type": "one_click_diagnostics_not_release_acceptance",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "device": facts["device"],
        "executable": facts["executable"],
        "automated_checks": checks,
        "manual_acceptance": manual,
        "manual_status_counts": counts,
        "limitations": [
            "This report does not independently verify user-entered manual observations.",
            "Microphone enumeration does not test actual recording, recognition accuracy, or speech quality.",
            "Registered SAPI voices do not prove audible playback or Hindi-language support.",
            "Screen, UI grounding, multi-step, verification, offline-answer, memory, and stability checks require real-device manual testing.",
            "No network requests, AI model downloads, app launches, clicks, audio recordings, or system-setting changes are performed.",
            "A diagnostic PASS is not M10.4 release acceptance; the evidence still requires review.",
        ],
    }

    directory = _report_directory()
    if directory is None:
        report["report_write_status"] = "failed"
        output_func("\n[FAIL] Could not find a writable report folder; no report was saved.")
        return report

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    report_path = directory / f"Vyom_Diagnostic_{stamp}.json"
    try:
        report_path.write_text(
            json.dumps(report, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    except OSError:
        report["report_write_status"] = "failed"
        output_func("\n[FAIL] Could not save the diagnostic report.")
        return report

    report["report_write_status"] = "saved"
    output_func("\nManual summary: " + ", ".join(f"{key}={value}" for key, value in counts.items()))
    output_func(f"Report saved: {report_path}")
    output_func("Share this JSON report for review; do not edit not_run entries to pass.")
    return report
