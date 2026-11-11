# Vyom M10.4 — One-Click Device Diagnostics

**Status:** implementation is part of M10.4; exact-SHA CI and real-device execution are pending until the workflow and user report are reviewed.

## Run it

Start the packaged **Vyom.exe** on a supported Windows PC. At the normal Vyom prompt, enter **diagnostics** or **3**. No separate Python installation, paid API, model download, or network connection is needed.

The runner writes a timestamped JSON report to **Documents\VyomDiagnostics**. If that location is not writable, it tries the Windows temporary directory. The report prints its exact location.

## Automated, read-only checks

- Windows version against the current Windows 8.1 / version 6.3 Python 3.11 baseline.
- Total and currently available physical RAM, without inventing a pass/fail RAM threshold.
- Presence of the core reasoning, action, UI, and voice module paths.
- SpeechRecognition, PyAudio, pyttsx3, and pywinauto dependency availability.
- Microphone device enumeration count only; no audio is recorded.
- Count of registered Windows SAPI voices only; no speech is played.
- Whether the paid-provider environment override is enabled.
- Running executable filename and SHA-256, without storing its full path.

## Guided manual evidence

The runner asks for the same ten M10.4 observations used by the PowerShell collector: screen observation, typed startup/exit, Hindi/Hinglish text, microphone/STT/audible TTS, UI grounding, multi-step dependencies, postcondition verification, honest unknown on provider outage, memory consent/opt-out, and low-memory stability.

Each status accepts **pass**, **fail**, **block**, or **not_run**. Blank or invalid input stays **not_run**. Notes are limited to 240 characters and obvious credential-like patterns are redacted. Do not enter passwords, API keys, transcripts, clipboard contents, or private document text.

## Safety and evidence limits

This is an environment diagnostic and evidence helper, not an independent examiner. It does not launch or close applications, click, type into other apps, capture the screen, record audio, change system settings, install packages, download models, or make network requests. It does not prove that speech was audible, that Hindi STT understood a sentence, or that a UI/task workflow succeeded.

Manual observations are user-entered and explicitly marked as not independently verified. Device compatibility and automated check results do not clear the M10.4 release gate. Share the JSON report for review; do not change a not_run or fail result to pass without rerunning the actual test.

M10.4 remains active until supported-device evidence and manual failures are reviewed and remediated. M10.5 must not start based on a green CI run or diagnostic report alone.
