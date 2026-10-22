# Vyom Phase State — Canonical Cross-Chat Handoff

This is the authoritative phase register for continuing work across chats. Read it first before each phase, then verify the branch head, detailed checkpoint, roadmap, and the newest exact-commit GitHub Actions run. Chat history alone is not the source of truth.

## Repository
- Repository: [snchat78-svg/Vyom](https://github.com/snchat78-svg/Vyom)
- Active branch: `updated`
- Detailed phase history: [VYOM_PHASE_CHECKPOINTS.md](VYOM_PHASE_CHECKPOINTS.md)
- Ordered roadmap: [VYOM_MIND_DEVELOPMENT_ROADMAP.md](VYOM_MIND_DEVELOPMENT_ROADMAP.md)
- Reusable cross-project policy: [PHASE_CONTINUITY_STANDARD.md](PHASE_CONTINUITY_STANDARD.md)
- Cross-project navigation index: [CROSS_PROJECT_PHASE_INDEX.md](CROSS_PROJECT_PHASE_INDEX.md)

## Last verified completed phase — M7.7
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

## Last verified completed phase — M7 Audit
- **M7.1–M7.7 combined source-grounded answers acceptance audit**
- Exact tested code/test commit: `59b8880d0c63d359c681615a77e53ee5c917d255`
- Exact-SHA CI: [run 39786556563](https://github.com/snchat78-svg/Vyom/actions/runs/39786556563) — **success**.
- CI result: **387 tests passed, 30 subtests passed**; tracked Python syntax checks, core/voice imports, complete test suite, clean build, Windows EXE build/verification, and `Vyom_EXE` artifact upload passed.
- Combined regressions passed: deliberately weak/future-dated source metadata does not override numeric or semantic conflict outcomes; matching excerpts served from separate hostnames remain `independent_corroboration=not_established` and are flagged as potential reposts.
- M7.7 continues to report freshness, evidence sufficiency, attribution, specificity and duplicate/repost metadata. Missing publication dates remain unknown; quality scores are metadata heuristics, not truth probabilities. Very short/boilerplate or weak-metadata primary evidence stays unknown with its citation.
- M7 automated acceptance is complete. Limitations: source quality is a bounded heuristic, duplicate checks cover only excerpts retrieved in the current lookup, publisher independence is not verified, and GitHub CI does not prove live external-network/TLS reliability or real interaction with the user's Windows desktop/microphone.

## Next phase — READY, NOT STARTED
- **M8 — General reasoning / sourced-answer evaluation**
- Start from `docs/VYOM_MIND_DEVELOPMENT_ROADMAP.md`; inspect the current reasoning/provider path before changing it.
- Build a deterministic evaluation matrix for provider outages/fallbacks, sourced versus unknown answers, uncertain intent/evidence, and how claims from M7 are kept qualified. Reuse the existing M7 source/evidence contract rather than duplicating retrieval, DNS guards, source scoring or contradiction logic.
- Preserve explicit citations and unresolved status when evidence is weak or conflicting. Never turn heuristic quality metadata into a probability that a claim is true.
- Mark M8 complete only after its own tests and exact-SHA full CI pass.

## M7 automated acceptance — completed
1. M7.1 public-source boundary, URL checks, bounded responses and honest unknown results.
2. M7.2 multi-source excerpt comparison, normalized-host deduplication, numeric/date disagreement handling.
3. M7.3 DNS public-destination preflight and redirect checks.
4. M7.4 DNS-pinned HTTP/HTTPS transport and proxy isolation.
5. M7.5 bounded configurable provider contract, fallthrough and output/fetch caps.
6. M7.6 cautious semantic contradiction signals with unresolved conflict status.
7. M7.7 source-quality metadata and unknown-on-weak-evidence guard.
8. Combined M7 audit: conflict precedence survives weak metadata, and same excerpts on separate hostnames do not establish independence. Full exact-SHA CI passed.

## Remaining M7 gate
1. **Overall M7 audit:** combined M7.1–M7.7 acceptance review and exact-SHA CI.
2. Start M8 only after the overall M7 gate passes; do not skip ahead.
 
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
