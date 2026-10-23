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

## Next phase — READY, NOT STARTED
- **M10.2 — Reproducible metrics runner and baseline**
- Build a deterministic offline runner over the M10.1 corpus. Each scenario must record whether it was run, the observed contract outcome, expected outcome and pass/fail rationale. Never count unrun scenarios as passes.
- Define metric numerators and denominators before publishing rates: intent/interpretation correctness, unsafe-guess rate, action-verification correctness, completion/recovery, epistemic-status correctness and latency. Report sample sizes and exclusions.
- Runner tests must use synthetic fixtures/stubbed providers and must not perform live web requests, microphone capture or desktop actions in CI. Separate live integration evidence for M10.4.
- M10.2 is complete only after exact-SHA full CI emits and validates a machine-readable run report plus a reproducible metrics summary. Then proceed to M10.3 CI regression thresholds.

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
- Current status: M8 complete; M9.1 is the only next phase. M10 is a cross-cutting evaluation track and its final release gate remains blocked until the roadmap's benchmark and real Windows acceptance requirements have evidence.

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
