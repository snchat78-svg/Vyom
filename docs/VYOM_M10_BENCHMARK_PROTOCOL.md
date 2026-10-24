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
- **M10.2 implementation (in progress):** `tools/vyom_benchmark_runner.py` compares M10.1 expected contract labels with the separate synthetic adapter observations in `tests/fixtures/m10_2_stub_observations.json`. Tests live in `tests/test_m10_2_metrics_runner.py`.

## M10.2 — Reproducible metrics runner and baseline

- CI runs the deterministic offline runner and emits `artifacts/m10_2/benchmark_report.json` plus `artifacts/m10_2/metrics_summary.json`; both are uploaded as `Vyom_M10_2_Benchmark_Baseline`.
- Every scenario has `pass`, `fail`, `error` or `unrun` status with expected/observed contract outcome, rationale and synthetic signals. Unrun or errored scenarios are excluded from denominators and never counted as passes.
- Metrics have explicit sample sizes and numerator/denominator rules: scenario-contract conformance, intent/interpretation correctness, unsafe-guess rate, action-verification correctness, task-completion/recovery correctness and epistemic-status correctness.
- **Measurement limit:** observations are fixed synthetic fixtures. The runner measures reproducibility and harness/contract-label conformance only. It does not exercise the Vyom application; its baseline is not product accuracy, live safety, task completion or latency. `product_latency_ms` remains `not_measured` until a separately instrumented runtime harness is used.
- Unknown scenario IDs/outcomes, duplicates, malformed signals and invalid corpus input fail closed. Fixed inputs produce byte-deterministic JSON.
- **Acceptance passed:** exact-SHA [run 40070421856](https://github.com/snchat78-svg/Vyom/actions/runs/40070421856) on `5daeb9c5ec83bccb41a96f362c4141282551640f` — **449 tests + 30 subtests**, syntax/core/voice imports, deterministic runner/report validation, clean build, Windows EXE verification, and upload of both report files passed. `Vyom_M10_2_Benchmark_Baseline` artifact ID: `12550488787`.

## M10.3 — CI regression thresholds (in progress)
- Thresholds are for deterministic synthetic harness conformance only; do not present them as measured product accuracy or safety.
- The threshold checker will validate the full 15-scenario fixture, expected denominator contracts, zero stub invariant violations, all required metric numerator/denominator/rate relationships, and the unmeasured product latency/accuracy boundary.
- CI will fail on a threshold breach and upload the machine-readable gate report.
- **Next after M10.3:** M10.4 — real Windows integration and release exit gate.
