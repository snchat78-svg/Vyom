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

## Code and test changes covered by latest exact-SHA CI

Exact code/test commit 1144c8de227a2a5d344ddf3aa17a7f5792305b3a; [GitHub Actions run 40631719205](https://github.com/snchat78-svg/Vyom/actions/runs/40631719205) passed **473 tests + 30 subtests**, Python syntax/core/voice imports, full test suite, clean build, M10.2 report validation, M10.3 threshold checks **22/22**, Windows EXE verification, CI-host smoke and artifact uploads.

- command_engine/intent.py: added common STT aliases such as van, wan and won, and handled numeric selection prefixes followed by noisy trailing words. Shared parser is used by voice and typed routes.
- voice/text_to_speech.py: on Windows, local eSpeak NG now attempts WAV rendering and synchronous playback through winsound; if that route fails, the existing direct eSpeak fallback remains. Tests use fake audio/playback APIs; hardware acceptance is still outstanding.
- ai_core/web_knowledge.py: bounded diagnostics log provider name, stage and exception type only. Raw query strings, URLs, response content, credentials and secret-bearing exception messages are excluded from the diagnostic structure. Safe-URL, DNS and fetch limits remain intact.
- ai_core/response_engine.py and command_engine/executor.py: unknown/conflicting source outcomes are preserved in the structured turn status; unknown/conflict is not reported as a successful fact.
- Regression coverage: selection phrase aliases/long-noisy choices, the Windows WAV helper and invalid-WAV rejection, provider diagnostics without raw error data, and unknown/conflict status propagation/early-return tracking.

## Still required for M10.4

1. Download Vyom_M10_4_Target_Device_Package (artifact ID 12792081432) from the run above, extract it and read README_FIRST.txt.
2. Run its preflight on the actual target PC and return M10_4_preflight.json. Confirm Windows version, architecture, memory and EXE checks; current Python 3.11 package requires Windows 8.1/version 6.3 or newer.
3. Only after preflight passes, perform and record real-device tests for audible Hindi/Hinglish output, number one/number van selection, source lookup and honest unknown behavior, microphone/STT, UI grounding, multi-step postconditions, provider outage/opt-out and low-memory stability. Return M10_4_target_device_evidence.json.

**Status stays BLOCKED until those target-device checks are supplied and reviewed.** Do not mark M10.4 complete from CI alone, and do not begin M10.5 early.
