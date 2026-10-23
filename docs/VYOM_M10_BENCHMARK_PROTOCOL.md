# M10.1 — Representative benchmark corpus and protocol

**Status:** M10.1 completed on exact-SHA [run 39913443550](https://github.com/snchat78-svg/Vyom/actions/runs/39913443550) at `5841279846599e349dedaadd942ce7736e6c82c2` — 440 tests + 30 subtests, Windows EXE verified/uploaded. Fixture set: `tests/fixtures/m10_1_vyom_benchmark_corpus.json`.
**Contract tests:** `tests/test_m10_1_benchmark_corpus.py`.

## Purpose and boundaries

This corpus defines synthetic, deterministic acceptance contracts for the M10 release-evaluation track. It is not an accuracy result and does not claim that every scenario has been executed by the current harness. The initial gate verifies corpus completeness, stable expected outcomes, safety invariants and absence of real private conversation/credential data. M10.2 adds a reproducible runner and baseline metrics.

## Coverage

The 15 scenarios cover English, Hindi, Roman Hindi, Hinglish, noisy STT, ambiguous target selection, multi-step dependency ordering, sourced factual answers, honest unknowns, conflicting sources, reasoning-provider outages, retrieval outages, uncertain-action recovery, post-action verification and memory opt-out/prompt-injection boundaries.

## Oracle style

Expected outcomes are contract labels with explicit `must_hold` and `must_not` checks, rather than hard-coded factual answers. For web retrieval, the acceptable contract can be a cited answer **or an honest unknown**, depending on available evidence. Conflicting claims must remain unresolved. A dispatched action without observed postconditions is not a completed action. These avoid brittle tests that depend on live websites or a hosted model.

## Privacy and reproducibility

Every current fixture is synthetic and marked `contract_only_not_benchmarked`. Do not commit actual transcripts, names, account details, API keys, passwords, clipboard payloads or private files. Live-network, microphone and real Windows desktop runs are kept separate from deterministic CI.

## M10.1 acceptance record

The exact-SHA full CI gate passed on `5841279846599e349dedaadd942ce7736e6c82c2` in [run 39913443550](https://github.com/snchat78-svg/Vyom/actions/runs/39913443550): 440 tests + 30 subtests; syntax/import checks, clean build, Windows EXE verification and artifact upload.

## Exit criteria for M10.1

- The corpus file is schema-versioned, IDs are unique and all required language/safety categories are covered.
- Each scenario has complete input/preconditions and a bounded expected contract.
- Ambiguity, conflict, unknown-answer, recovery, verification and memory-safety outcomes have explicit non-negotiable invariants.
- Contract tests pass under exact-SHA full CI.
- **Next: M10.2 — reproducible metrics runner and baseline.** It must establish denominator rules and measured results from executed scenarios; never report corpus coverage as model accuracy.
