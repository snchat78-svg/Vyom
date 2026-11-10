VYOM M10.4 TARGET-DEVICE PACKAGE
=================================

This package contains:
- Vyom.exe
- vyom_windows_acceptance.ps1
- M10_4_WINDOWS_ACCEPTANCE.md
- this README

No Python installation is required for the EXE or preflight script.

STEP 1 — EXTRACT
Extract every package file into one normal local folder. Keep Vyom.exe and
vyom_windows_acceptance.ps1 together. Do not run this package from inside the
ZIP viewer.

STEP 2 — CHECK WINDOWS VERSION AND RUN A HARMLESS PREFLIGHT
Open Command Prompt in the extracted folder and run:

powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\vyom_windows_acceptance.ps1 -ExePath .\Vyom.exe -OutputPath .\M10_4_preflight.json -AttemptLaunchSmokeTest

The script checks OS version, visible RAM, EXE presence/hash/size and, only if
the OS is supported, sends the harmless "exit" command to the EXE. It does not
record audio, click other apps, or modify your documents. It creates
M10_4_preflight.json in this folder.

IMPORTANT COMPATIBILITY GATE
The current EXE uses the Python 3.11 runtime baseline, which supports Windows
8.1/version 6.3 and newer. Windows 8.0/version 6.2 is unsupported for this
build. If the report says blocked_unsupported_os or the command returns exit
code 2, stop here; do not mark app tests as passed. A separately reviewed
packaging decision would be needed to support that older OS. Do not install
Python just to run these checks.

STEP 3 — ONLY IF THE OS IS SUPPORTED, COLLECT MANUAL ACCEPTANCE
After the first report confirms a supported OS and the EXE starts/exits
successfully, run:

powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\vyom_windows_acceptance.ps1 -ExePath .\Vyom.exe -OutputPath .\M10_4_target_device_evidence.json -AttemptLaunchSmokeTest -CollectManualEvidence

Answer each checklist prompt based only on a test you actually performed:
pass, fail, block, or not_run. Blank or invalid entries remain not_run.
Notes must be short and non-sensitive. Do not enter passwords, API keys,
private transcripts, clipboard content, or personal file contents.

STEP 4 — RETURN THE REPORTS
Attach M10_4_preflight.json and, if collected, M10_4_target_device_evidence.json
in the Vyom project chat so the evidence can be reviewed. These are
user-entered reports and are not independently verified until reviewed.
Do not edit not_run entries to pass.

The actual target-device gate remains open until supported-device evidence is
reviewed. GitHub Actions results alone are not proof of your PC's behavior.
