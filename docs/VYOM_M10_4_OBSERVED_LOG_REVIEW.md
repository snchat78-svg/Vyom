# M10.4 observed EXE log review — 2026-10-28

## Evidence boundary
The user supplied an excerpt from a real local Vyom EXE session on 2026-10-28. It is treated as partial observed evidence for debugging, not as a completed acceptance checklist. The raw log is intentionally not copied into the repository. Successful GitHub CI is not evidence of physical speaker output or real-device OS compatibility.

## Findings from the supplied log

| Area | Observed result | Meaning |
|---|---|---|
| TTS and wake | SAPI initialized; eSpeak NG Hindi was selected; wake word was recognized; physical microphone capture was repeatedly released before TTS | Startup and wake/session path ran. TTS response completed: True alone does not prove sound was audible through the user's speaker. |
| Pending app selection | notapaid kholo returned Notepad and Notepad++ choices. The next phrases number van and a longer number 1 vala not kaise kholen did not select the pending item and went through fresh goal routing | This was a reproducible STT alias/selection-normalization gap. |
| Incorrect follow-up resolution | A long selection utterance was interpreted as an unrelated file/version query with many unrelated options | Selection routing should keep priority only when a pending list exists; arbitrary standalone number mentions must remain normal questions. |
| Factual retrieval | Capital-of-India and Rajasthan-district questions reached WebKnowledge, whose result reason was no_source_or_network_unavailable; Vyom gave an honest unknown answer | Retrieval could not return a safe source on that run. This does not establish whether DNS, socket, TLS, remote filtering or page markup was the exact cause; provider diagnostics were added rather than guessing. |
| Structured status | The no-source response text was honest but the executor still reported success=True for the overall conversation stage | New structured status propagates unknown/conflict instead of calling the factual answer successful. The message still goes to console and TTS. |

## Cross-check of regressions and verified fixes

The second submitted log was traced through the live branch and compared with the older `fix/universal-resolver-file-folder` branch. The older and current `ToolManager._handle_launcher_response` used the same broad resolver fallback; the current branch had accumulated more fuzzy discovery. The generic phonetic matcher also awarded a 0.90 substring score even when a one-character piece matched, explaining why a misspelled app target could become unrelated A.JPG/MP3/Dart candidates.

The factual-query stall had a separate root cause: the intent detector treated “vhat is kaipital off indiya” as unknown, and synchronous production DNS lookup could outlive the overall retrieval deadline because `socket.getaddrinfo` itself had no timeout.

## Code and test changes covered by latest exact-SHA CI

Exact code/test commit `c4434d45be1bcf472100fc7d2c7b1847c4e0e135`; [GitHub Actions run 40817785734](https://github.com/snchat78-svg/Vyom/actions/runs/40817785734) passed **482 tests + 30 subtests**, syntax/core/voice imports, full suite, clean build, M10.2 baseline validation, M10.3 threshold checks **22/22**, Windows EXE build/verification, CI-host preflight and artifact uploads.

- `ai_core/web_knowledge.py`: bounded daemon DNS with worker cap/cache/deadline; timeouts return control so provider fallback can finish. A bounded STT normalizer repairs common English question errors and phonetic English WH words in Devanagari. `ai_core/response_engine.py` logs lookup elapsed/status/reason and avoids exposing raw transport exception text.
- `command_engine/intent.py`: noisy factual questions route directly to the response/knowledge path instead of waiting for semantic action planning. Action-prefix phrases stay on the command path.
- `tools/tool_manager.py` and `tools/universal_resolver.py`: failed app lookup no longer triggers unrestricted fuzzy local-file searching; file/folder fallback checks exact paths and plausible common-location matches. Exact short names remain usable, and explicit file requests keep the file resolver.
- `tools/phonetic_matcher.py` and `tools/universal_app_launcher.py`: short strings are not treated as high-confidence fuzzy matches. Selection and app suggestions remain available for sufficiently distinctive candidates.
- Hindi TTS: current local eSpeak NG WAV + Windows playback attempt and direct eSpeak fallback are preserved. The log proves the playback function returned, not that sound was physically audible.

## Latest artifacts and remaining M10.4 gate

- [Exact-SHA run 40817785734](https://github.com/snchat78-svg/Vyom/actions/runs/40817785734): `Vyom_EXE` ID `12873471349` (expires 2026-11-05), `Vyom_M10_4_Target_Device_Package` ID `12873456416` (expires 2026-11-28), CI preflight ID `12873272240`, M10.2 baseline ID `12873003736`, M10.3 gate report ID `12873008824`.
- From the run's Artifacts section, download the target-device package, extract it, read `README_FIRST.txt` and run preflight on the actual PC. Return `M10_4_preflight.json`. If supported, run real-device checks and return `M10_4_target_device_evidence.json`.
- Python 3.11 requires Windows 8.1/version 6.3 or newer; Windows 8.0/version 6.2 is unsupported. Confirm the actual OS.

**Status remains BLOCKED until the real target-device evidence is returned and reviewed.** CI does not prove physical speaker output, microphone quality, live user-network DNS/TLS, real desktop postconditions or low-memory behavior. Do not mark M10.4 complete or begin M10.5 yet.
