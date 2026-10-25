# M10.4 — Real Windows integration and release exit gate

**Status:** in progress. GitHub CI has not performed acceptance on the user's physical computer. The PowerShell preflight and CI-host smoke test are evidence helpers, not a substitute for target-device validation.

## M10.3 predecessor gate

M10.3 passed on exact commit ec5f4753e6e386cdd50d5cf508de78732939862a in [GitHub Actions run 40077787538](https://github.com/snchat78-svg/Vyom/actions/runs/40077787538): 459 tests + 30 subtests, 22/22 synthetic threshold checks, clean build, Windows EXE verification, and uploads for Vyom_EXE, Vyom_M10_2_Benchmark_Baseline and Vyom_M10_3_Regression_Gate. This is synthetic harness-conformance evidence only; it is not measured product accuracy, safety, or latency.

## Platform compatibility is a hard preflight

The current EXE workflow builds with Python 3.11. The official Python 3.11 Windows documentation says this runtime supports Windows 8.1 and newer; Windows 8.0 is below that baseline: https://docs.python.org/3.11/using/windows.html

The preflight script therefore treats Windows version 6.2 (Windows 8.0) as BLOCKED and version 6.3 (Windows 8.1) or newer as eligible for further testing. Do not interpret a launch failure on Windows 8.0 as a confirmed application defect, and do not mark release acceptance complete on that OS. Supporting Windows 8.0 would require a separately reviewed packaging/support decision; silently falling back to an end-of-life Python runtime is not an acceptable release shortcut.

The script records installed RAM but does not invent a hard memory threshold. On low-memory devices, responsiveness, audio stability, and crashes must be observed directly.

## No-Python preflight and harmless launch check

The script is compatible with Windows PowerShell 3+ and does not require a Python installation. Download it from the repository and run from the folder containing the downloaded EXE/script (or specify the EXE path):

    powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\tools\vyom_windows_acceptance.ps1 -ExePath .\Vyom.exe -OutputPath .\M10_4_preflight.json -AttemptLaunchSmokeTest

It writes a JSON report before returning. Exit code 2 means the OS is below the current Python 3.11 support baseline; exit code 1 means host facts, file inspection, or the optional launch smoke check failed. The smoke check sends only the harmless text command "exit"; it does not click controls, type into other applications, record microphone audio, or modify user files.

For an interactive target-device checklist, run the same script on the target Windows computer with `-CollectManualEvidence` added. It prompts for each test and accepts only `pass`, `fail`, `block`, or `not_run`; blank or invalid input stays `not_run`. It refuses to collect manual evidence on GitHub Actions and blocks app testing when the OS is unsupported or the EXE is missing/invalid. User-entered statuses and notes are not independently verified and still require review. Notes are bounded and credential-like patterns are redacted, but do not enter secrets or private content.

CI runs the same script on the GitHub Actions host and uploads Vyom_M10_4_CI_Preflight. A green CI-host smoke test proves only that the script and EXE can start and exit on that host.


## Latest target-device package — available

The combined package was built and uploaded by exact-SHA [GitHub Actions run 40190738625](https://github.com/snchat78-svg/Vyom/actions/runs/40190738625) from code/test commit `50c5a18c75daa2e16f11dd6e455065554996dcfe`. Artifact: `Vyom_M10_4_Target_Device_Package` (ID 12598460548; expires 2026-11-24). Download it from the run page's **Artifacts** section. It includes `Vyom.exe`, `vyom_windows_acceptance.ps1`, this checklist and `README_FIRST.txt`.

The run passed **464 tests + 30 subtests**, Python syntax/import checks, clean build, M10.2/M10.3 gates, Windows EXE verification, CI-host smoke and target-package upload. This is build/CI evidence only; it does not prove the user's computer passed.

Use `README_FIRST.txt` to run the preflight without installing Python. If the preflight reports Windows 8.0/version 6.2, stop: the current Python 3.11 build requires Windows 8.1/version 6.3 or newer. If the OS is supported and the harmless launch check succeeds, perform only checklist items you actually ran, then attach the JSON reports for review. Do not mark `not_run` as `pass`.

## One-download target-device package

The Windows workflow now creates a separate `Vyom_M10_4_Target_Device_Package`
artifact containing `Vyom.exe`, the PowerShell preflight/evidence collector,
this acceptance checklist, and `README_FIRST.txt` with the exact no-Python
commands. Download it from the latest green [Vyom Actions run](https://github.com/snchat78-svg/Vyom/actions).

Run the first preflight before filling any manual checklist. The package blocks
the current Python 3.11 build on Windows 8.0/version 6.2; Windows 8.1/version
6.3 or newer is the documented baseline. If unsupported, return the preflight
JSON and do not mark manual tests pass. If supported, collect the explicit
manual report and attach both JSON reports for review. GitHub-hosted tests
remain CI-host evidence only.

## Manual target-device acceptance checklist

Keep each item's status as not_run until it has been performed on the target Windows device. Record pass/fail, a short non-sensitive observation, OS version, and the relevant report filename. Do not collect API keys, passwords, raw transcripts, personal clipboard contents, or screenshots of private documents.

| Test ID | Acceptance step | Pass condition | Evidence status |
|---|---|---|---|
| typed_startup_and_exit | Launch the EXE, enter a benign typed greeting/status command, then exit. | Starts without crash; normal exit; no Python install needed. | not_run |
| hindi_and_hinglish_text | Try representative Hindi, Roman Hindi and Hinglish text commands. | Meaning is preserved; ambiguity requests clarification rather than guessing. | not_run |
| microphone_stt_and_tts | Enter voice mode and use a harmless greeting/status utterance in a quiet room. | Voice is captured and recognized; TTS is audible; unavailable devices are reported clearly. | not_run |
| ui_grounding | Use a non-destructive app/window task with an unambiguous target. | Correct target/window is observed; ambiguous targets are rejected or clarified. | not_run |
| multi_step_dependencies | Run a reversible multi-step task with a clear prerequisite and inspect the sequence. | Dependent steps do not run before prerequisites. | not_run |
| postcondition_verification | Ask Vyom to perform a reversible UI action and inspect the resulting state. | It reports success only if the postcondition is actually observed; otherwise it reports unverified/failed. | not_run |
| provider_outage_unknown_answer | With connectivity unavailable, ask a factual question that requires web retrieval. Restore connectivity after the check. | It returns a qualified unknown/outage response and does not fabricate a sourced answer. | not_run |
| memory_consent_and_opt_out | Check memory consent and opt out using the documented memory CLI. | Consent starts OFF; opt-out blocks memory use; action authority is not granted by memory. | not_run |
| low_memory_stability | Repeat a small safe task while observing system responsiveness and crashes. | No repeatable hang/crash; note measured RAM use without treating a synthetic threshold as product evidence. | not_run |

## Latest CI-host preflight result

Exact-SHA [run 40078621691](https://github.com/snchat78-svg/Vyom/actions/runs/40078621691) passed on commit 806565b798238853e16f611a742104da46df02d9: 459 tests + 30 subtests, 22/22 M10.3 threshold checks, Windows EXE verification, a clean-exit smoke test, and artifact upload. The preflight JSON reported overall_status=preflight_passed_manual_acceptance_pending. Artifact: Vyom_M10_4_CI_Preflight (ID 12554685802). This confirms the CI host only; the table above remains not_run until actual target-device evidence is supplied.

## Release evidence and exit criteria

1. Capture the preflight JSON and confirm the OS baseline is supported.
2. Fill the manual acceptance statuses only after each test has actually been run; include concise non-sensitive observations.
3. If any check fails, leave M10.4 in progress and open/fix the corresponding defect; never convert not-run into pass.
4. The final release gate requires M10.3's synthetic regression gate, M9.1–M9.5 safety gates, and target-device evidence for UI grounding, voice/STT/TTS, provider outage, multi-step order and verified postconditions.
5. A report from GitHub Actions is labelled github_actions_runner and cannot be used as evidence that the user's own Windows installation passed.

## Current known platform risk

The previously reported device is Windows 8 64-bit with 2 GB RAM. The OS-version probe must distinguish Windows 8.0 from Windows 8.1. If it reports version 6.2, current Python 3.11-based packaging is outside its documented baseline and the real-device phase remains blocked pending a supported OS or a separately reviewed packaging decision. The 2 GB RAM value is a resource-risk observation, not a pass/fail threshold.


## Evidence collector implementation CI (2026-10-25)

Exact-SHA [run 40175621834](https://github.com/snchat78-svg/Vyom/actions/runs/40175621834) passed on `c025c32b9ae0f4e29339e2c26c8e3d0a589e06fd`: 463 tests + 30 subtests, 22/22 M10.3 threshold checks, Windows EXE build/verification, CI-host clean-exit smoke, and artifacts. The first implementation run failed on a PowerShell parsing issue; the follow-up commit corrected it and passed. This remains CI-host evidence only; no target-device acceptance is claimed.
