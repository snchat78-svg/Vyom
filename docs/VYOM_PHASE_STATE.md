# Vyom Phase State — Canonical Cross-Chat Handoff

This is the authoritative phase register for continuing work across chats. Read it first before each phase, then verify the branch head, detailed checkpoint, roadmap, and the newest exact-commit GitHub Actions run. Chat history alone is not the source of truth.

## Repository
- Repository: [snchat78-svg/Vyom](https://github.com/snchat78-svg/Vyom)
- Active branch: `updated`
- Detailed phase history: [VYOM_PHASE_CHECKPOINTS.md](VYOM_PHASE_CHECKPOINTS.md)
- Ordered roadmap: [VYOM_MIND_DEVELOPMENT_ROADMAP.md](VYOM_MIND_DEVELOPMENT_ROADMAP.md)
- Reusable cross-project policy: [PHASE_CONTINUITY_STANDARD.md](PHASE_CONTINUITY_STANDARD.md)
- Cross-project navigation index: [CROSS_PROJECT_PHASE_INDEX.md](CROSS_PROJECT_PHASE_INDEX.md)

## Last verified completed phase — M7.6
- **M7.6 — Broader semantic contradiction detection**
- Exact tested tree: `6d5101f10a2c35d2f2bf2699d2960db861f6dfd9`
- Exact-SHA CI: [run 39757311244](https://github.com/snchat78-svg/Vyom/actions/runs/39757311244) — **success**.
- CI result: **380 tests passed, 28 subtests passed**; syntax/import checks, clean build, Windows EXE build/verification and `Vyom_EXE` artifact upload passed.
- Behavior: keeps numeric/date conflict precedence and adds `potential_semantic_conflict` for selected non-numeric opposing predicate/negation signals when sentence context overlaps. Conflicts return `answer_status=conflicting_sources` and state that the claims remain unresolved; no source is automatically declared correct.
- Regression coverage: open/closed, negation, permitted/prohibited paraphrase, unrelated statements, compatible differently worded claims, Hindi open/closed and an end-to-end unresolved answer.
- Limitation: this is a bounded, auditable rule-based signal—not general semantic understanding or a language model. Implicit, low-overlap, unlisted-antonym and nuanced multilingual contradictions may remain unresolved. Do not claim M7 is complete.

## Active phase — M7.7 IN PROGRESS (exact-SHA CI pending)
- **M7.7 — Source-quality evaluation**
- Code/tests add bounded metadata scoring for explicit publication freshness, excerpt sufficiency/boilerplate, source attribution, content specificity and exact/near-duplicate excerpts across the retrieved set.
- Per-source quality is attached to `sources[]` and summarized under `evidence.source_quality`. Missing/unparseable dates are labelled `unknown` rather than treated as stale. Duplicate detection is limited to the current retrieved excerpts.
- Very short/boilerplate or weak-metadata primary evidence is kept `answer_status=unknown` with its citation retained. Numeric/semantic source conflicts retain conflict precedence.
- These are heuristic metadata assessments only—not truth probabilities, proof of source independence, or an authority ranking. Exact-SHA full CI must pass before M7.7 is marked complete.

## Remaining M7 gate
1. **M7.7:** source-quality evaluation and its regression matrix.
2. Re-audit M7.1–M7.7 together. Start M8 only after the whole M7 acceptance gate passes.

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
- 2026-10-22: M7.7 implementation and regression tests committed; exact-SHA CI pending. The quality score remains metadata-only and is not a probability of truth. M7 remains partial until M7.7's test gate and the overall M7 audit both pass.
