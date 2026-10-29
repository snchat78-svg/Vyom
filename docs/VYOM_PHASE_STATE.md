# Vyom Phase State — Canonical Cross-Chat Handoff

This is the authoritative phase register for continuing work across chats. Read it first before each phase, then verify the branch head, detailed checkpoint, roadmap, and the newest exact-commit GitHub Actions run. Chat history alone is not the source of truth.

## Repository
- Repository: [snchat78-svg/Vyom](https://github.com/snchat78-svg/Vyom)
- Active branch: `updated`
- Detailed phase history: [VYOM_PHASE_CHECKPOINTS.md](VYOM_PHASE_CHECKPOINTS.md)
- Ordered roadmap: [VYOM_MIND_DEVELOPMENT_ROADMAP.md](VYOM_MIND_DEVELOPMENT_ROADMAP.md)
- Reusable cross-project policy: [PHASE_CONTINUITY_STANDARD.md](PHASE_CONTINUITY_STANDARD.md)
- Cross-project navigation index: [CROSS_PROJECT_PHASE_INDEX.md](CROSS_PROJECT_PHASE_INDEX.md)

## Previous verified phase — M8
- **M8 — General reasoning / sourced-answer evaluation**
- Exact tested code/test commit: `0253010a1df4837a926631a63ad27042ce1f0d87`
- Exact-SHA GitHub Actions: [run 39899815866](https://github.com/snchat78-svg/Vyom/actions/runs/39899815866) — **success**.
- CI result: **395 tests passed, 30 subtests passed**; Python syntax, core/voice imports, clean build, Windows EXE build/verification and `Vyom_EXE` artifact upload all passed.
- Behavior: response handling now treats `answer_status` as authoritative over an inconsistent provider `success` flag. `conflicting_sources` remains unresolved; `unknown` and weak evidence do not promote answer text into a fact; source URLs are retained for sourced, inferred, weak, and conflicting results; inferred output is explicitly labelled as inference; provider-reported `known` status is not described as independent verification.
- Regression matrix: Hindi/English conflict responses; deliberately inconsistent success+conflict and success+unknown payloads; weak evidence; citation retention; sourced excerpt; inferred answer; provider outage; deterministic conversational fallback. Existing gateway/Local Qwen tests continue to cover Gemini 429 fallback and offline/configuration cases.
- Limitations: provider status/evidence metadata is not independent proof. Source quality and conflict detection remain bounded heuristics. GitHub CI does not prove live network/TLS quality or actual user-machine microphone/desktop acceptance.

## Previous verified phase — M7.7
- **M7.7 — Source-quality evaluation**
- Exact tested code/test commit: `98d7855c83b35cc37dadc01c4245c3803219394f`
- Exact-SHA CI: [run 39785293786](https://github.com/snchat78-svg/Vyom/actions/runs/39785293786) — **success**.
- CI result: **385 tests passed, 28 subtests passed**; syntax/import checks, clean build, Windows EXE build/verification and `Vyom_EXE` artifact upload all passed.
- Behavior: each retrieved source now exposes a bounded metadata assessment for explicit publication freshness, excerpt sufficiency/boilerplate, attribution, specificity and duplicate/repost signals within the currently retrieved set. Missing or unparsable dates remain `unknown`; the score is not a probability of truth. Quality metadata is returned both per source and under `evidence.source_quality`.
- Safety: a very short/boilerplate or weak-metadata primary excerpt becomes `answer_status=unknown` while retaining the citation. Numeric and semantic conflict outcomes keep precedence; quality scores never select a winner or upgrade source claims into proven facts.
- Limitations: this is a bounded heuristic, not independent publisher verification or broad originality search. Repost detection compares only retrieved excerpts; a fresh date can be incorrect or reflect a page update rather than the claim's original publication. Live external network/TLS, the user's actual Windows desktop and microphone remain outside GitHub CI.

## Previous verified phase — M7.6
- **M7.6 — Broader semantic contradiction detection**
- Exact tested tree: `6d5101f10a2c35d2f2bf2699d2960db861f6dfd9`
- Exact-SHA CI: [run 39757311244](https://github.com/snchat78-svg/Vyom/actions/runs/39757311244) — **success**, 380 tests and 28 subtests.
- Bounded, context-gated polarity/opposition rules identify selected non-numeric contradictions; claims remain unresolved. Implicit, low-overlap, unlisted-antonym and nuanced multilingual contradictions may remain unresolved.

## Previous verified phase — M7 Audit
- **M7.1–M7.7 combined source-grounded answers acceptance audit**
- Exact tested code/test commit: `59b8880d0c63d359c681615a77e53ee5c917d255`
- Exact-SHA CI: [run 39786556563](https://github.com/snchat78-svg/Vyom/actions/runs/39786556563) — **success**.
- CI result: **387 tests passed, 30 subtests passed**; tracked Python syntax checks, core/voice imports, complete test suite, clean build, Windows EXE build/verification, and `Vyom_EXE` artifact upload passed.
- Combined regressions passed: deliberately weak/future-dated source metadata does not override numeric or semantic conflict outcomes; matching excerpts served from separate hostnames remain `independent_corroboration=not_established` and are flagged as potential reposts.
- M7.7 continues to report freshness, evidence sufficiency, attribution, specificity and duplicate/repost metadata. Missing publication dates remain unknown; quality scores are metadata heuristics, not truth probabilities. Very short/boilerplate or weak-metadata primary evidence stays unknown with its citation.
- M7 automated acceptance is complete. Limitations: source quality is a bounded heuristic, duplicate checks cover only excerpts retrieved in the current lookup, publisher independence is not verified, and GitHub CI does not prove live external-network/TLS reliability or real interaction with the user's Windows desktop/microphone.

## Previous verified phase — M9.1
- **M9.1 — Opt-in learning baseline and memory-schema inventory**
- Exact tested code/test commit: `9fa8f8bde39611079e4bce170e77a955d8794432`
- Exact-SHA full CI: [run 39900778509](https://github.com/snchat78-svg/Vyom/actions/runs/39900778509) — **success**.
- CI result: **399 tests passed, 30 subtests passed**; Python syntax/core/voice imports, clean build, Windows EXE build/verification and `Vyom_EXE` artifact upload passed.
- Deliverables: `docs/VYOM_M9_MEMORY_INVENTORY.md`, proposed design-only `docs/schemas/vyom_user_memory.v1.schema.json`, deterministic tests in `tests/test_m9_1_memory_inventory.py`, and .gitignore rules for local skill registry JSON/temp files.
- Findings: `SessionMemory` and conversation history are bounded in-process context; `SkillRegistry` separately persists skill goal/plan JSON, while the recovery journal is already a minimal fail-closed marker that excludes action payloads.
- Limits: this was an inventory/schema gate only. The proposed schema is not wired to runtime storage; no persistent personal memory or automatic learning was enabled. Runtime validation, user consent, deletion verification and OS-level privacy protections remain later acceptance work.

## Previous verified phase — M9.2
- **M9.2 — Explicit opt-in and record-level approval**
- Exact tested code/test commit: `2401889a7efa0248736e196961063db160f09a6c`
- Exact-SHA full CI: [run 39901852967](https://github.com/snchat78-svg/Vyom/actions/runs/39901852967) — **success**.
- CI result: **408 tests passed, 30 subtests passed**; Python syntax/core/voice imports, clean build, Windows EXE build/verification and `Vyom_EXE` upload passed.
- Behavior: typed CLI exposes session-only opt-in/withdrawal, pending review, separate per-record approval and fail-closed write authorization. Consent defaults OFF; withdrawal clears session approvals; restart resets consent.
- Limits: M9.2 implemented consent and approval gates only. No long-term memory file was added in that phase; subsequent storage needs schema validation and lifecycle controls. SkillRegistry capability-goal persistence remains a separate retention boundary.

## Previous verified phase — M9.4
- **M9.4 — Memory review, export and deletion**
- Exact code/test commit: `eb9707498708f1e92bf5ebdf92f491642db95cdf`
- Exact-SHA full CI: [run 39908005080](https://github.com/snchat78-svg/Vyom/actions/runs/39908005080) — **success**.
- CI result: **427 tests passed, 30 subtests passed**; tracked Python syntax, critical/core/voice imports, clean build, Windows EXE build/verification and `Vyom_EXE` artifact upload all passed.
- Deliverables: consent-gated `memory list` and `memory inspect <memory-id>`; export to a new absolute JSON path; delete one or all records with durable-state verification.
- Safety: review/export require current session consent; deletion remains available after opt-out. Export excludes expired/inactive records, validates the stored schema, rejects unsafe paths and never overwrites an existing destination. Corrupt/unsupported stores fail closed.
- Limits: export uses a caller-selected filesystem path; the user remains responsible for protecting that destination. Consent still resets at process restart. Real Windows desktop interaction remains a separate manual check.

## Previous verified phase — M9.5
- **M9.5 — Safe learning integration and M9 exit audit**
- Exact tested code/test commit: `6f9a99e05555c8c25ac6bcb546934aa6f61d1afc`
- Exact-SHA full CI: [run 39912869937](https://github.com/snchat78-svg/Vyom/actions/runs/39912869937) — **success**.
- CI result: **436 tests passed, 30 subtests passed**; tracked Python syntax, core/voice imports, clean build, Windows EXE build/verification and artifact upload succeeded.
- Behavior: only allow-listed presentation preferences (`response_language`, `response_style`, `verbosity`, `explanation_level`, `answer_format`) with enumerated values are projected into reasoning context. Arbitrary memory text, correction records, workflow summaries, expired/revoked/unapproved records and conflicting preferences are ignored.
- Safety: global/application scope filters are conservative; the memory store must allow the current consent state. A store read failure supplies no hints. The current goal is passed unchanged; memory does not create capabilities, alter safety gates, bypass confirmation or assert execution success. Action-risk confirmation remains independently enforced.
- Limitations: the hints are advisory metadata; deterministic local reasoning may ignore presentation preferences. The suite does not replace live Windows microphone/UI/network acceptance.

## Last verified completed phase — M10.1
- **M10.1 — Representative benchmark corpus**
- Exact tested code/test commit: `5841279846599e349dedaadd942ce7736e6c82c2`
- Exact-SHA full CI: [run 39913443550](https://github.com/snchat78-svg/Vyom/actions/runs/39913443550) — **success**.
- CI result: **440 tests passed, 30 subtests passed**; tracked Python syntax, core/voice imports, clean build, Windows EXE build/verification and `Vyom_EXE` artifact upload passed.
- Deliverables: `tests/fixtures/m10_1_vyom_benchmark_corpus.json` (15 synthetic scenarios), `tests/test_m10_1_benchmark_corpus.py` (coverage/contract checks), and `docs/VYOM_M10_BENCHMARK_PROTOCOL.md`.
- Coverage: English, Hindi, Roman Hindi, Hinglish, noisy STT, ambiguity, compound dependencies, web-grounded or unknown answers, conflicting sources, provider outage, uncertain recovery, post-action verification and memory safety.
- Limits: this phase verifies corpus structure and deterministic expected contracts only. It is explicitly `contract_only_not_benchmarked`; no intent accuracy, unsafe-guess rate, latency or real-world completion metric has been measured. Live network and user-machine Windows/audio acceptance remain pending.

## Last verified completed phase — M10.2
- **M10.2 — Reproducible metrics runner and synthetic baseline**
- Exact tested branch commit: `5daeb9c5ec83bccb41a96f362c4141282551640f`
- Exact-SHA full CI: [run 40070421856](https://github.com/snchat78-svg/Vyom/actions/runs/40070421856) — **success**.
- Results: **449 tests passed, 30 subtests passed**; Python syntax/core/voice imports, complete test suite, offline benchmark report validation, clean build, Windows EXE build/verification and both report/EXE artifact uploads passed.
- Artifacts: `Vyom_M10_2_Benchmark_Baseline` (artifact ID `12550488787`) and `Vyom_EXE` (artifact ID `12551071242`).
- Metrics/report disclose scenario labels, counts, sample sizes and metric numerator/denominator. Missing observations count as errors, unselected scenarios stay unrun and are excluded, and product latency remains `not_measured`.
- **Boundary:** fixed synthetic observations validate harness wiring and contract-label conformance only. They are not measurements of actual Vyom accuracy, safety, task completion, or performance.

## Last verified completed phase — M10.3
- **M10.3 — CI regression thresholds**
- Exact tested commit: ec5f4753e6e386cdd50d5cf508de78732939862a
- Exact-SHA full CI: [run 40077787538](https://github.com/snchat78-svg/Vyom/actions/runs/40077787538) — **success**.
- CI result: **459 tests passed, 30 subtests passed**; M10.2 report generation/validation passed; M10.3 threshold gate reported **22 checks passed, 0 failed**; clean build, Windows EXE verification and artifact uploads passed.
- Artifacts: Vyom_EXE (12553818070), Vyom_M10_2_Benchmark_Baseline (12553669304), and Vyom_M10_3_Regression_Gate (12553967403).
- Measurement boundary: thresholds apply only to the fixed synthetic benchmark/harness. They do not measure live product accuracy, safety, completion or latency.

## Current phase — IN PROGRESS
- **M10.4 — Real Windows integration and release exit gate** remains active. Automated regression fixes are CI-verified; target-device acceptance/release remains blocked.
- **Latest code/test SHA:** `c4434d45be1bcf472100fc7d2c7b1847c4e0e135`; exact-SHA [GitHub Actions run 40817785734](https://github.com/snchat78-svg/Vyom/actions/runs/40817785734) — **success**.
- **CI result:** **482 tests passed, 30 subtests passed**; Python syntax, core/voice imports, full suite, clean build, M10.2 benchmark validation, M10.3 synthetic threshold gate (**22/22 pass**), Windows EXE build/verification, CI-host executable smoke preflight and artifact uploads passed.
- **Regression findings:** synchronous production DNS could outlive the overall retrieval deadline; “vhat is kaipital off indiya” could be routed to semantic planning instead of factual retrieval; and app-launch misses could fall through to fuzzy file search, producing unrelated A.JPG/MP3/Dart options.
- **Fixes:** `ai_core/web_knowledge.py` uses a bounded daemon DNS resolver with worker cap, short cache and deadline-aware timeout. `command_engine/intent.py` routes recognized noisy factual questions directly to the response layer. The query normalizer repairs a narrowly bounded set of common STT errors; `ai_core/response_engine.py` logs lookup elapsed/status/reason and avoids raw exception logging. `tools/tool_manager.py` and `tools/universal_resolver.py` separate app fallback from unrestricted fuzzy file scans. The shared phonetic matcher no longer gives tiny substrings an artificial high score. Direct/exact paths and exact short filenames remain supported.
- **Hindi TTS boundary:** existing local eSpeak NG WAV + synchronous Windows playback and direct eSpeak fallback remain present. The submitted log showed playback code completed but does not independently prove audible sound from the physical speaker.
- **Artifacts from [run 40817785734](https://github.com/snchat78-svg/Vyom/actions/runs/40817785734):** `Vyom_EXE` ID `12873471349` (expires **2026-11-05**); `Vyom_M10_4_Target_Device_Package` ID `12873456416` (expires **2026-11-28**); `Vyom_M10_4_CI_Preflight` ID `12873272240`; M10.2 and M10.3 reports IDs `12873003736` and `12873008824`.
- **Next step:** download the target-device package from the run's **Artifacts** section, extract it and read `README_FIRST.txt`; run preflight on the actual PC and provide `M10_4_preflight.json`. If preflight passes, collect `M10_4_target_device_evidence.json` for actual Hindi/Hinglish audio, noisy-question retrieval, “number one/number van” selection, PDF/JPG/folder open, provider outage, UI grounding, multi-step postconditions and low-memory behavior.
- **Still BLOCKED:** actual target-device JSON/manual acceptance has not been reviewed. CI cannot prove live DNS/TLS from the user's network, audible speaker output, microphone/STT quality or desktop postconditions. Python 3.11 requires Windows 8.1/version 6.3 or newer; Windows 8.0/version 6.2 is unsupported. Confirm the exact OS before manual acceptance.
- **Release gate:** remain **BLOCKED** until supported target-device preflight and real-device evidence are supplied and reviewed. Do not mark M10.4 complete or advance to M10.5 based on CI alone.

## M7 automated acceptance — completed
1. M7.1 public-source boundary, URL checks, bounded responses and honest unknown results.
2. M7.2 multi-source excerpt comparison, normalized-host deduplication, numeric/date disagreement handling.
3. M7.3 DNS public-destination preflight and redirect checks.
4. M7.4 DNS-pinned HTTP/HTTPS transport and proxy isolation.
5. M7.5 bounded configurable provider contract, fallthrough and output/fetch caps.
6. M7.6 cautious semantic contradiction signals with unresolved conflict status.
7. M7.7 source-quality metadata and unknown-on-weak-evidence guard.
8. Combined M7 audit: conflict precedence survives weak metadata, and same excerpts on separate hostnames do not establish independence. Full exact-SHA CI passed.

## M7 gate — completed
- M7.1–M7.7 combined source-grounded acceptance and the M7 audit passed on exact-SHA [run 39786556563](https://github.com/snchat78-svg/Vyom/actions/runs/39786556563), with 387 tests and 30 subtests, syntax/import checks, clean build, Windows EXE verification and artifact upload.
- M8 then passed its own full exact-SHA CI on [run 39899815866](https://github.com/snchat78-svg/Vyom/actions/runs/39899815866), with 395 tests and 30 subtests, syntax/import checks, clean build, Windows EXE verification and artifact upload.
- Current status: M7/M8 and M9.1–M9.5 automated gates are complete; M10.1–M10.3 automated gates are complete. M10.4 is active, but the final release gate remains blocked until supported target-device Windows/audio/UI evidence exists.

## Cross-chat and cross-project continuity rules
- This file, the checkpoint and roadmap are durable handoff records. Update them whenever a phase changes status.
- Before work in any repository, read that repository's canonical phase-state file, verify branch/head/latest CI, then choose only the next incomplete phase.
- Never repeat a phase whose exact tested SHA has a successful CI run unless a new requirement or regression explicitly requires a revisit.
- If tests or CI fail, keep the same phase in progress and fix it; do not skip to a later phase.
- Mark complete only when the exact code/test SHA passes the required full CI. Record the SHA, run URL/result, test count, limitations and next phase.
- This repository contains a reusable policy template at `docs/PHASE_CONTINUITY_STANDARD.md`. It does **not** automatically change every other repository; each other project needs its own canonical phase register and an adopted copy of the policy.
- Do not claim local Windows UI, microphone, production network or interactive desktop acceptance based only on GitHub CI.

## Change log
- 2026-10-22: M7.3 DNS preflight passed on `72815257ca2f7deb89a82b86bee17c904536414a` in [run 39741822185](https://github.com/snchat78-svg/Vyom/actions/runs/39741822185).
- 2026-10-22: M7.4 DNS-pinned transport passed on `f417bebeecd902bbfe1111bbad623eaaaeceb4a0` in [run 39746025751](https://github.com/snchat78-svg/Vyom/actions/runs/39746025751).
- 2026-10-22: M7.5 configurable retrieval providers passed on `90ae4ead63c586b8da98191d5266254736c5269d` in [run 39753595589](https://github.com/snchat78-svg/Vyom/actions/runs/39753595589): 373 tests and 28 subtests.
- 2026-10-22: M7.6 semantic contradiction signals passed on `6d5101f10a2c35d2f2bf2699d2960db861f6dfd9` in [run 39757311244](https://github.com/snchat78-svg/Vyom/actions/runs/39757311244): 380 tests and 28 subtests, Windows EXE verification/upload.
- 2026-10-22: M7.7 passed exact-SHA CI on `98d7855c83b35cc37dadc01c4245c3803219394f` in [run 39785293786](https://github.com/snchat78-svg/Vyom/actions/runs/39785293786): 385 tests + 28 subtests, Windows EXE verified/uploaded. Source-quality scoring remains metadata-only, not a probability of truth.
- 2026-10-22: M7 combined acceptance audit passed on `59b8880d0c63d359c681615a77e53ee5c917d255` in [run 39786556563](https://github.com/snchat78-svg/Vyom/actions/runs/39786556563): 387 tests + 30 subtests; syntax/import, clean build, Windows EXE verification and artifact upload passed. Conflicting claims remain unresolved when metadata is weak; duplicate cross-host excerpts do not establish independence. M7 automated acceptance complete; M8 is next and not started.

- 2026-10-23: M8 passed exact-SHA CI on `0253010a1df4837a926631a63ad27042ce1f0d87` in [run 39899815866](https://github.com/snchat78-svg/Vyom/actions/runs/39899815866): 395 tests + 30 subtests, syntax/import checks, clean build, Windows EXE verification and `Vyom_EXE` upload. M9.1 opt-in learning baseline and memory-schema inventory is next.

- 2026-10-23: M9.1 started after M8 passed exact-SHA run 39899815866. Current baseline inventory, design-only schema and tests are in progress; long-term personal-memory runtime remains disabled.

- 2026-10-23: M9.1 passed exact-SHA full CI on `9fa8f8bde39611079e4bce170e77a955d8794432` in [run 39900778509](https://github.com/snchat78-svg/Vyom/actions/runs/39900778509): 399 tests + 30 subtests, syntax/import checks, clean build, Windows EXE verification/upload. M9.2 explicit opt-in and record-level approval is next.

- 2026-10-23: M9.2 started after M9.1 passed exact-SHA run 39900778509. Consent is session-only and default-off; no persistent personal-memory write path is enabled.

- 2026-10-23: M9.2 passed exact-SHA CI on `2401889a7efa0248736e196961063db160f09a6c` in [run 39901852967](https://github.com/snchat78-svg/Vyom/actions/runs/39901852967): 408 tests + 30 subtests, syntax/import checks, clean build, Windows EXE verification/upload. M9.3 implementation followed.

- 2026-10-23: M9.3 code/test commit `e9dde6a8629cdb6e7641c95ad44448e34bcffabb` passed exact-SHA [run 39905813305](https://github.com/snchat78-svg/Vyom/actions/runs/39905813305): 419 tests + 30 subtests, syntax/import checks, clean build, Windows EXE verification/upload.

- 2026-10-23: M9.3 passed exact-SHA full CI on `de32220023fca744089edcd0311a0d2234a4daae` in [run 39906002229](https://github.com/snchat78-svg/Vyom/actions/runs/39906002229): 419 tests + 30 subtests, syntax/import, clean build, Windows EXE verification/upload. M9.4 review/export/deletion is next.

- 2026-10-23: M9.4 passed exact-SHA CI on `eb9707498708f1e92bf5ebdf92f491642db95cdf` in [run 39908005080](https://github.com/snchat78-svg/Vyom/actions/runs/39908005080): 427 tests + 30 subtests, syntax/import checks, clean build, Windows EXE verification/upload. M9.5 safety integration and exit audit is next.

- 2026-10-23: M9.5 passed exact-SHA CI on `6f9a99e05555c8c25ac6bcb546934aa6f61d1afc` in [run 39912869937](https://github.com/snchat78-svg/Vyom/actions/runs/39912869937): 436 tests + 30 subtests; Windows EXE verified/uploaded. M10.1 representative benchmark corpus is in progress.

- 2026-10-23: M10.1 passed exact-SHA CI on `5841279846599e349dedaadd942ce7736e6c82c2` in [run 39913443550](https://github.com/snchat78-svg/Vyom/actions/runs/39913443550): 440 tests + 30 subtests; syntax/import checks, clean build, Windows EXE verification/upload. M10.2 reproducible metrics runner and baseline is next.

- 2026-10-24: M10.2 started on `137a3375892f4945f2213a2df39180b7509139c2`; offline synthetic-adapter runner, report schema, denominator tests and CI artifact integration added. Exact-SHA gate is pending.

- 2026-10-24: M10.2 passed exact-SHA full CI on `5daeb9c5ec83bccb41a96f362c4141282551640f` in [run 40070421856](https://github.com/snchat78-svg/Vyom/actions/runs/40070421856): 449 tests + 30 subtests; benchmark report validation, Windows EXE verification and both artifacts succeeded. M10.3 CI regression thresholds is now in progress.

- 2026-10-24: M10.3 passed exact-SHA CI on ec5f4753e6e386cdd50d5cf508de78732939862a in [run 40077787538](https://github.com/snchat78-svg/Vyom/actions/runs/40077787538): 459 tests + 30 subtests, 22/22 synthetic checks, EXE and gate artifacts uploaded. M10.4 real Windows integration and release evidence is in progress; Python 3.11 makes Windows 8.0 a compatibility blocker.

- 2026-10-24: M10.4 preflight helper passed CI-host smoke on exact commit 806565b798238853e16f611a742104da46df02d9 in [run 40078621691](https://github.com/snchat78-svg/Vyom/actions/runs/40078621691): 459 tests + 30 subtests, 22/22 M10.3 threshold checks, EXE and all benchmark/preflight artifacts uploaded. Device microphone/UI acceptance remains not_run.

- 2026-10-25: M10.4 evidence-collector implementation passed exact-SHA CI on `c025c32b9ae0f4e29339e2c26c8e3d0a589e06fd` in [run 40175621834](https://github.com/snchat78-svg/Vyom/actions/runs/40175621834): 463 tests + 30 subtests, 22/22 synthetic thresholds, EXE verification, CI-host smoke and artifacts. M10.4 remains in progress pending supported target-device evidence.

- 2026-10-25: M10.4 target-device package created on exact code/test commit `50c5a18c75daa2e16f11dd6e455065554996dcfe` in [run 40190738625](https://github.com/snchat78-svg/Vyom/actions/runs/40190738625): 464 tests + 30 subtests, EXE build/verification, M10.2/M10.3 gates, CI-host smoke and artifact `Vyom_M10_4_Target_Device_Package` (ID 12598460548). Device acceptance is still blocked pending the user's actual Windows report.

- 2026-10-28: Reviewed user-provided EXE log and fixed shared STT choice recovery, added Windows WAV playback attempt for Hindi eSpeak, added secret-safe retrieval failure diagnostics, and made unknown/conflicting source outcomes visible in structured turn status. Exact-SHA run [40631719205](https://github.com/snchat78-svg/Vyom/actions/runs/40631719205) passed on 1144c8de227a2a5d344ddf3aa17a7f5792305b3a: 473 tests + 30 subtests, M10.2/M10.3 gates, EXE verification and fresh M10.4 package. M10.4 remains blocked on real supported target-device evidence.

- 2026-10-29: Log regressions fixed on `c4434d45be1bcf472100fc7d2c7b1847c4e0e135`; exact-SHA [run 40817785734](https://github.com/snchat78-svg/Vyom/actions/runs/40817785734) passed 482 tests + 30 subtests, M10.2/M10.3 gates, EXE verification, CI-host preflight and artifacts. M10.4 remains blocked pending real target-device evidence.
