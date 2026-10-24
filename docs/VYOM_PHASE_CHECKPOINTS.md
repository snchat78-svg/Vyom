# Vyom Phase Checkpoint Ledger

This file is the hand-off record across conversations. The repository code and CI are authoritative; this ledger points to the evidence and the next uncompleted task. Never restart a phase just because a new chat begins.

## Re-entry protocol (mandatory)

1. Read this ledger and `docs/VYOM_MIND_DEVELOPMENT_ROADMAP.md`.
2. Inspect the current `updated` branch head and newest GitHub Actions run for that exact SHA.
3. Read the target module and relevant tests; compare them with the phase checklist below.
4. Mark each acceptance item `implemented + tested`, `partial`, or `missing`. Search existing code/tests and commit history before proposing any change.
5. Implement only the first unmet acceptance item in dependency order. Do not recreate completed functionality in another module.
6. Update this ledger and roadmap in the same commit as the phase change. A phase is CI-verified only when the workflow for the same commit succeeds. A green CI does not claim real Windows/microphone validation unless that validation was actually performed.

## Checkpoint snapshot

- Branch: `updated`
- Verified M0.3 implementation: `3feb985aad0fe5c6c31c1be6189b7363f6a0d616`, [CI run 39399731304](https://github.com/snchat78-svg/Vyom/actions/runs/39399731304) succeeded with 299 passed and 12 subtests; EXE build/upload succeeded.
- Verified M0.4 implementation: `a499f3e61a30b7a5afb4ed3aacba47406c7fe06b`, [CI run 39400224264](https://github.com/snchat78-svg/Vyom/actions/runs/39400224264) succeeded with 300 passed and 12 subtests; Windows `Vyom.exe` built, verified and uploaded.
- M0.3 reuses existing M4 WorldState history and M5/M6 verification output; do not rebuild observers/verifiers.
- M0.4 routes typed and spoken turns through the same `ConversationManager` instance. The former direct text-to-executor bypass is covered by `tests/test_m0_4_shared_frontend.py`.
- M0 exit-gate audit implementation: `b92d277ebdb5a9bb49469612e4388b1979ff044c`, [CI run 39401980752](https://github.com/snchat78-svg/Vyom/actions/runs/39401980752) succeeded for the exact SHA. The full suite passed; Windows EXE build, verification, and artifact upload succeeded. The change added bounded payload-free mission plan topology and tested text/voice executor and verification parity.
- M0.1–M0.4 and the M0 automated exit gate are implemented and CI-tested. Real Windows, microphone, and cross-app interaction checks remain external validation.
- M1 payload-preservation repair `144909deaf50575b3b999337c895ab237d355c23` passed exact-SHA [CI run 39403055826](https://github.com/snchat78-svg/Vyom/actions/runs/39403055826).
- M1 confidence-margin guard `c87d406f3057a0497e6943301fe849b41ea6bf68` passed exact-SHA [CI run 39404026850](https://github.com/snchat78-svg/Vyom/actions/runs/39404026850).
- Direct AppsFolder ambiguity and tab-delimited parser correction `3f0b172edc5f3d69737da0eff4ad2ed97521b3f0` passed exact-SHA [CI run 39404982337](https://github.com/snchat78-svg/Vyom/actions/runs/39404982337).
- M1 final acceptance suite `6a7054de0828949f1f1bcade33a06cb9438fa192` passed exact-SHA [CI run 39405455918](https://github.com/snchat78-svg/Vyom/actions/runs/39405455918), including the full suite and Windows EXE build/verification/upload. Real audio/desktop acceptance remains external.
- Current M2 patch fixes target suppression in the semantic frame and adds target/payload separation, ambiguity alternatives and same-plan paraphrase tests. Exact-SHA CI pending.

## Current verified handoff — M10.3 passed; M10.4 in progress
- M10.1 corpus exact-SHA CI: [run 39913443550](https://github.com/snchat78-svg/Vyom/actions/runs/39913443550) passed on 5841279846599e349dedaadd942ce7736e6c82c2 with 440 tests + 30 subtests.
- M10.2 runner exact-SHA CI: [run 40070421856](https://github.com/snchat78-svg/Vyom/actions/runs/40070421856) passed on 5daeb9c5ec83bccb41a96f362c4141282551640f with 449 tests + 30 subtests.
- M10.3 threshold gate passed on exact commit ec5f4753e6e386cdd50d5cf508de78732939862a in [run 40077787538](https://github.com/snchat78-svg/Vyom/actions/runs/40077787538): 459 tests + 30 subtests and 22/22 threshold checks; Windows EXE and all M10.2/M10.3 artifacts were uploaded.
- **M10.4 implementation checkpoint:** exact-SHA [run 40078621691](https://github.com/snchat78-svg/Vyom/actions/runs/40078621691) passed on commit 806565b798238853e16f611a742104da46df02d9 with 459 tests + 30 subtests, 22/22 synthetic threshold checks, Windows EXE verification, and uploaded Vyom_M10_4_CI_Preflight artifact (ID 12554685802).
- **Current phase:** M10.4 — real Windows integration and release exit gate. The PowerShell 3-compatible preflight and harmless clean-exit smoke passed on GitHub's host; real UI/audio cases remain not_run.
- **Platform risk:** Python 3.11's documented Windows baseline is Windows 8.1 (version 6.3) or newer. The previously reported Windows 8.0/version 6.2 host is outside this baseline; no release acceptance can be claimed until the actual OS version is checked and a supported target is tested.
- A CI-host smoke report is not target-device evidence. Manual UI grounding, microphone/STT/TTS, compound tasks, postcondition verification, provider outage/unknown response and low-memory stability remain pending.

## Current phase hand-off

- **Authoritative cross-chat tracker:** [`docs/VYOM_PHASE_STATE.md`](VYOM_PHASE_STATE.md). Read this file first before starting a phase; update it whenever phase status changes. Completed phases must be backed by an exact-commit CI run. Never restart a completed phase; resume the recorded in-progress phase or select the next explicitly listed incomplete item.

- M2 target-preservation patch `d40edb47ebc0be055c7a3b337661e70dcf80f11a` passed exact-SHA [CI run 39405929075](https://github.com/snchat78-svg/Vyom/actions/runs/39405929075); explicit generic UI targets such as `click Save` remain in the meaning frame.
- M2 confidence/hypothesis increment `d0dd7910c32169f1884759254e47b969c38429c8` passed exact-SHA [CI run 39415383368](https://github.com/snchat78-svg/Vyom/actions/runs/39415383368), including complete tests and Windows EXE build/verification/upload. Low/invalid-confidence action hypotheses stay unresolved.
- M2 local-semantic dispatch gate `74c6ec0c5f0baafd40272bf32342ee00d0dbc268` passed exact-SHA [CI run 39416145129](https://github.com/snchat78-svg/Vyom/actions/runs/39416145129): low-confidence executable plans and tied target candidates return terminal clarification with an empty plan.
- Stateless-normalization regression `7a92d936ab84322610bb7f6ab15725ea90fc36ed` passed exact-SHA [CI run 39416613583](https://github.com/snchat78-svg/Vyom/actions/runs/39416613583); unknown targets do not become learned aliases across turns. Persistent user-approved learning remains opt-in M9 work.
- Terminal-route precedence and no-plan guard `d1001544bd50dd308fe7293132aa4c72be2b0e2e` passed exact-SHA [CI run 39417115798](https://github.com/snchat78-svg/Vyom/actions/runs/39417115798), including complete tests and Windows EXE build/verification/upload. Terminal semantic clarification now outranks any stale model/contextual plan and yields no execution steps. M2 automated confidence, target-preservation, correction-state and route-precedence gates are green; noisy-voice benchmark and actual Windows desktop/microphone validation remain external. M3 audit follows without claiming M2 platform validation.
- M3 first increment `7e7cdd4aa604b6e71b3fdc0532f8a336ce5781d2` passed exact-SHA [CI run 39418664644](https://github.com/snchat78-svg/Vyom/actions/runs/39418664644), including 330+ passing tests and Windows EXE build/verification/upload. High-impact plans are held before MissionRuntime starts; unrelated commands cannot bypass pending confirmation; explicit confirm reuses the stored plan and cancel discards it. Risk heuristics remain conservative and app-specific risk coverage plus real desktop acceptance remain incomplete.
- Shared-front-end integration commit `20ef8416e82b6095ad7a91a345db4ad0bcd65e75` passed exact-SHA [CI run 39419318845](https://github.com/snchat78-svg/Vyom/actions/runs/39419318845). `command_engine.executor.execute("confirm action")` resumes the stored pending plan; `execute("cancel action")` discards it without starting the runtime. Complete tests and Windows EXE build/verification/upload passed. App-specific risk coverage and real desktop acceptance remain incomplete.
- Devanagari risk-label increment `b354be672afb30a1bb236b0e844fbf8a239ca1be` passed exact-SHA [CI run 39420557346](https://github.com/snchat78-svg/Vyom/actions/runs/39420557346): complete tests, syntax/import checks, Windows EXE build/verification/upload all succeeded. Tests cover Hindi deletion/account closure/payment/publishing labels, safe keyboard events, Save clicks and free-form typed payload isolation. Heuristic app-specific coverage and real desktop acceptance remain incomplete.
- M3 expanded risk coverage for account deletion/disablement, subscription/order changes, token revocation, integration disconnects and publication; exact-SHA CI run 39427132026 passed. The failed-prerequisite integration test in commit `7a83b53186017645ce73bc9a277b3faa6107a6a0` passed exact-SHA CI run 39608106621, including complete tests, Windows EXE build/verification and artifact upload.
- M4.7 adds a cross-component contract test between `WorldStateModel.snapshot()` and `ContextActionCompiler`: fresh UI focus resolves a contextual target, while stale nested UI evidence is clarified rather than guessed. The combined M4.7–M4.12 acceptance passed exact-SHA CI run 39615193598 on `57b43cfd52f5ef6c95c150257165e640be22e101`; real Windows UIA validation remains pending.
- M4.8 changes `WorldStateModel.snapshot()` to skip clipboard reads unless callers explicitly pass `include_clipboard=True`; tests guard both non-reading defaults and authorized opt-in reads. Included in the successful combined M4.7–M4.12 exact-SHA run.
- M4.9 adds a foreground-coherence guard: UIStateObserver compares the active window at capture start/end; contextual compilation refuses explicitly incoherent snapshots. Tests cover a switched foreground window, a stable window and clarification from incoherent context. Included in the successful combined M4.7–M4.12 exact-SHA run.
- M4.10 rejects explicitly incoherent UI observations in the shared autonomous freshness validator, stopping re-planning before reasoning even when timestamps are fresh; regression tests cover the guard. Included in the successful combined M4.7–M4.12 exact-SHA run.
- M4.11 makes the mission re-planning boundary require `ui.available=True`; missing or unavailable UI evidence blocks re-reasoning even with a fresh wrapper timestamp. Tests protect generic-helper compatibility and the no-reasoning failure path. Included in the successful combined M4.7–M4.12 exact-SHA run.
- M4.12 tightens the strict re-planning gate to require a valid, fresh nested UI timestamp; tests reject missing and stale UI timestamps. Included in the successful combined M4.7–M4.12 exact-SHA run.
- M5.6 closes the execution-side coherence gap: explicit `coherent=False` blocks semantic target dispatch before an action, and an incoherent post-action snapshot cannot verify success. Regression tests cover both no-dispatch and no-false-success paths; combined M5.6–M5.7 exact-SHA CI passed in [run 39719715495](https://github.com/snchat78-svg/Vyom/actions/runs/39719715495).
- M5.7 requires timestamped, fresh UI evidence before semantic target dispatch and after action completion; stale/missing pre-action evidence blocks dispatch and stale post-action evidence cannot verify success. Regression tests cover finite numeric timestamps, booleans/non-numeric values, NaN/infinities, stale snapshots and excessive future skew. Exact-SHA CI passed on `b7f566773ee23139fdd507e19b19588d8c587c33`; real Windows UIA validation remains pending.
- M7.1 adds public-source retrieval guardrails: unsafe explicit redirect destinations are refused, response bodies are capped at 1 MB maximum, successful evidence carries source type/count and makes `inference_used=false`, `independent_corroboration=not_checked`, and `source_content_trust=untrusted` explicit; failed retrieval is marked unknown without a fabricated answer. Tests and full Windows EXE CI passed for `09a59277a978d645292ecf4892e45e24cd24d99a` in [run 39720196175](https://github.com/snchat78-svg/Vyom/actions/runs/39720196175). M7 is not complete: cross-source corroboration/conflict handling, provider configurability and defense against DNS-resolved private destinations still need dedicated work.
- M7.2 extends source retrieval beyond the first hit and conservatively compares evidence from distinct hostnames. Numeric/date-like differences in strongly overlapping sentence contexts remain unresolved instead of being guessed; hostname count does not establish publisher independence. Four regression tests plus the legacy singular-source contract test are covered. Exact-SHA CI passed for commit `aa744d7261200de32c897829158ef585d6b2308b` in [run 39730872062](https://github.com/snchat78-svg/Vyom/actions/runs/39730872062).
- M7.3 — DNS-aware public destination guard **passed exact-SHA CI** on `72815257ca2f7deb89a82b86bee17c904536414a` in [run 39741822185](https://github.com/snchat78-svg/Vyom/actions/runs/39741822185): full test suite, syntax/import checks, Windows EXE build, EXE verification, and artifact upload succeeded. DNS failures, empty answer sets, and non-global DNS results are blocked before fetches and redirects. The preflight-only transport still had a DNS time-of-check/time-of-use gap; M7.4 is addressing it.
- M7.4 — **transport-level DNS pinning passed exact-SHA CI** on `f417bebeecd902bbfe1111bbad623eaaaeceb4a0` in [run 39746025751](https://github.com/snchat78-svg/Vyom/actions/runs/39746025751). The actual HTTP/HTTPS connection validates every DNS answer and connects to the numeric sockaddr from that same answer set; HTTPS preserves the hostname for SNI/certificate checks and Host authority. Ambient proxies are disabled on this fetch path. Regression coverage includes numeric-IP pinning, mixed public/private rejection, malformed resolver output, TLS hostname preservation and opener policy. CI passed 364 tests and 28 subtests, syntax/import checks, Windows EXE build/verification and artifact upload. Live external-network/TLS behavior still requires real-environment validation; M7 remains incomplete. **Next: M7.5 configurable retrieval providers.**
- M7.5 — **configurable bounded retrieval providers passed exact-SHA CI** on `90ae4ead63c586b8da98191d5266254736c5269d` in [run 39753595589](https://github.com/snchat78-svg/Vyom/actions/runs/39753595589). Added the `RetrievalProvider` callback contract and routed the built-in Wikipedia/DuckDuckGo providers through it. Provider order/failure, unsafe citation rejection, empty-provider unknown fallback, normalized-host dedupe, malformed generator output, 4-provider cap, 3-results/provider cap, 6 results/lookup, 6 network fetches/provider / 12 total, and excerpt/title/site/URL/answer size limits are covered. `client.fetch_text()` applies the shared public URL/DNS-pinned transport and request caps; the backward-compatible singular `source` field remains. Exact-SHA CI passed 373 tests and 28 subtests, syntax/import checks, Windows EXE build/verification and artifact upload. Provider callbacks are local trusted code, not sandboxed; custom network code must use `fetch_text`. **Next: M7.6 broader semantic contradiction detection.**
- M7.6 — **broader semantic contradiction detection passed exact-SHA CI** on `6d5101f10a2c35d2f2bf2699d2960db861f6dfd9` in [run 39757311244](https://github.com/snchat78-svg/Vyom/actions/runs/39757311244). Added context-gated signals for selected opposing non-numeric predicates (open/closed, permitted/prohibited, safe/dangerous, true/false and selected Hindi pairs) and shared-context negation. Numeric/date conflict remains higher priority. Relation `potential_semantic_conflict` returns `answer_status=conflicting_sources` and explicitly leaves the claims unresolved. Seven regression tests cover non-numeric opposition, negation, paraphrased access wording, unrelated claims, compatible differently worded claims, Hindi open/closed, and the end-to-end unresolved response. First CI attempt surfaced a Hindi Unicode cue/anchor issue; the original-sentence cue matcher and cue-stripped anchor calculation corrected it. Final exact-SHA CI passed 380 tests and 28 subtests, syntax/import checks, Windows EXE build/verification and artifact upload. Limitations remain for implicit, low-overlap, unlisted-antonym and nuanced multilingual contradictions. **Next: M7.7 source-quality evaluation.**


## M8 detailed acceptance record
- Commit `0253010a1df4837a926631a63ad27042ce1f0d87`; exact-SHA CI [39899815866](https://github.com/snchat78-svg/Vyom/actions/runs/39899815866) passed with 395 tests and 30 subtests. The run passed Python syntax, core/voice import checks, the complete pytest suite, clean build, Windows EXE build/verification, and artifact upload.
- New coverage in `tests/test_m8_reasoning_evaluation.py`: conflict is unresolved even if a provider incorrectly reports success and includes an asserted answer; unknown/weak evidence is not promoted to a fact even with `success=True`; citations are retained; inferred output is labelled; provider exceptions and model unavailability preserve deterministic fallback behavior.
- Existing `tests/test_local_qwen_provider.py`, `tests/test_deep_reasoner_gateway.py`, `tests/test_response_engine_model_budget.py`, and voice integration tests cover provider fallback, invalid gateway output, deterministic factual lookup and offline-safe conversation/action paths.
- Limitation: metadata statuses are provider assertions, not independent proof; generated inference and quality heuristics are not fact verification. Real Windows/audio and live network behavior need separate acceptance evidence.


## M9.1 acceptance record — passed exact-SHA CI (2026-10-23)
- Existing components inspected: `memory/session_memory.py`, `memory/selection_manager.py`, `ai_core/skill_registry.py`, `ai_core/skill_builder.py`, `ai_core/mission_runtime.py`, `ai_core/conversation_manager.py`, `ai_core/model_gateway.py`, `ai_core/logger.py` and related tests.
- Deliverables: `docs/VYOM_M9_MEMORY_INVENTORY.md`, proposed `docs/schemas/vyom_user_memory.v1.schema.json`, and `tests/test_m9_1_memory_inventory.py`. A root ignore rule prevents default local skill-registry JSON/temp files from being committed accidentally.
- Exact-SHA [run 39900778509](https://github.com/snchat78-svg/Vyom/actions/runs/39900778509) passed: 399 tests + 30 subtests, Python syntax/core/voice imports, clean build, Windows EXE verification and artifact upload. No runtime long-term personal-memory storage was added. **Next: M9.2 explicit opt-in and record-level approval.**


## M9.2 acceptance record — passed exact-SHA CI (2026-10-23)
- `ai_core/memory_consent.py` and typed-text CLI hooks in `ai_core/main.py` implement default-off session consent, pending-candidate review, explicit per-record approval and fail-closed write authorization.
- `tests/test_m9_2_memory_consent.py` covers default-off, consent disclosure, separate approval, tamper/scope/expiry rejection, withdrawal, restart default-off and no disk writes.
- Exact-SHA [run 39901852967](https://github.com/snchat78-svg/Vyom/actions/runs/39901852967) passed on `2401889a7efa0248736e196961063db160f09a6c`: 408 tests + 30 subtests; syntax/import, clean build, Windows EXE verification and artifact upload succeeded.
- Consent/approval is session-only; M9.2 itself does not persist memory records.

## M9.3 acceptance record — passed exact-SHA CI (2026-10-23)
- `ai_core/user_memory_store.py`: local per-user versioned JSON store; strict envelope/record schema; cap 256 records/1 MB; atomic writes; no silent overwrite of corrupt/unsupported stores.
- `ai_core/memory_consent.py` and `ai_core/main.py`: typed proposal, review, per-record approval, and explicit save; reads gated by current consent; no automatic speech-transcript learning.
- `tests/test_m9_3_user_memory_store.py`: round-trip/reload, metadata retention, consent-off/restart, scope/expiry/lifecycle, structural tamper, corrupt/unknown/oversized store, explicit CLI approval/save and atomic-write rollback.
- Exact-SHA [run 39906002229](https://github.com/snchat78-svg/Vyom/actions/runs/39906002229) passed on `de32220023fca744089edcd0311a0d2234a4daae`: 419 tests + 30 subtests; syntax/import, clean build, Windows EXE verification and artifact upload succeeded.
- **Next: M9.4 — review, export and deletion.** Test durable file verification, safe user-selected export paths, no credentials/transcript leakage, delete-one/delete-all and reload-after-deletion.


## M9.4 hand-off — ready, not started
- Add inspection and export for the current user's approved records, plus delete-one/delete-all and durable verification. Never report deletion success if filesystem validation fails.
- Global opt-out must immediately block use; distinguish opt-out from deletion. All read/export paths must fail closed on a corrupt or unsupported store.
- Record M9.4 results in this ledger and canonical phase state only after exact-SHA full CI passes.


## M9.5 acceptance record — passed exact-SHA CI (2026-10-23)
- `ai_core/memory_learning_policy.py` projects only allow-listed presentation preferences with enumerated values; arbitrary stored text, corrections and workflow summaries do not enter the reasoning hints.
- `ai_core/autonomous_agent.py` adds the hints to compile/initial reasoning/replanning context without changing the user's goal. `ai_core/model_gateway.py` specifies advisory-only semantics; risk/confirmation and verification remain independent gates.
- `tests/test_m9_5_memory_learning_safety.py` covers scope, expiry, revoked/unapproved records, conflicting values, spoofed contracts, store-read failure, goal preservation and risk confirmation.
- Exact-SHA [run 39912869937](https://github.com/snchat78-svg/Vyom/actions/runs/39912869937) passed on `6f9a99e05555c8c25ac6bcb546934aa6f61d1afc`: 436 tests + 30 subtests; syntax/import, clean build and Windows EXE verification/upload succeeded.

## M10.1 acceptance record — passed exact-SHA CI (2026-10-23)
- Corpus: `tests/fixtures/m10_1_vyom_benchmark_corpus.json` — synthetic, versioned, contract-only cases.
- Protocol: `docs/VYOM_M10_BENCHMARK_PROTOCOL.md`; tests: `tests/test_m10_1_benchmark_corpus.py`.
- Acceptance checks required category coverage and language variants; every fixture has an expected outcome, must-hold and must-not constraints. No actual performance result is inferred from corpus coverage.
- Exact-SHA [run 39913443550](https://github.com/snchat78-svg/Vyom/actions/runs/39913443550) passed on `5841279846599e349dedaadd942ce7736e6c82c2`: 440 tests + 30 subtests; syntax/import checks, clean build, Windows EXE verification and artifact upload all succeeded.
- **Next: M10.2 — reproducible metrics runner and baseline.**


## M10.2 acceptance record — passed exact-SHA CI (2026-10-24)
- Exact tested branch commit `5daeb9c5ec83bccb41a96f362c4141282551640f`; [run 40070421856](https://github.com/snchat78-svg/Vyom/actions/runs/40070421856) succeeded with 449 tests + 30 subtests.
- Workflow step `Run M10.2 Offline Benchmark and Validate Report` passed after pytest. It generated and validated `artifacts/m10_2/benchmark_report.json` and `artifacts/m10_2/metrics_summary.json`.
- The Windows EXE was built and verified. Artifact `Vyom_M10_2_Benchmark_Baseline` (ID `12550488787`) and `Vyom_EXE` (ID `12551071242`) were uploaded.
- Baseline is fixed synthetic fixture/harness conformance only. Product accuracy/safety and product latency are explicitly not measured.

## M10.3 acceptance record — passed exact-SHA CI (2026-10-24)
- Exact-SHA run [40077787538](https://github.com/snchat78-svg/Vyom/actions/runs/40077787538) passed on ec5f4753e6e386cdd50d5cf508de78732939862a.
- Full test result: 459 tests + 30 subtests; M10.2 benchmark report passed validation; M10.3 threshold output reported 22 checks passed, 0 failed.
- Artifact outputs: Vyom_EXE ID 12553818070; Vyom_M10_2_Benchmark_Baseline ID 12553669304; Vyom_M10_3_Regression_Gate ID 12553967403.
- Product accuracy/safety/latency remain unmeasured by the synthetic runner.

## M10.4 work-in-progress checkpoint (2026-10-24)
- Add tools/vyom_windows_acceptance.ps1 and docs/VYOM_M10_4_WINDOWS_ACCEPTANCE.md. The script supports Windows PowerShell 3+, collects OS/version/architecture/RAM and EXE hash/size, then optionally sends only the harmless "exit" command to the EXE and verifies clean shutdown.
- Exact-SHA workflow [40078621691](https://github.com/snchat78-svg/Vyom/actions/runs/40078621691) ran that script against the CI-built EXE and uploaded Vyom_M10_4_CI_Preflight (ID 12554685802). Overall status was preflight_passed_manual_acceptance_pending. This verifies the host smoke helper only; it is not evidence that a user's machine passed.
- Manual acceptance IDs: typed startup/exit, Hindi/Hinglish text, microphone/STT/TTS, UI grounding, multi-step dependency order, postcondition verification, provider outage/unknown response, memory consent/opt-out and low-memory stability. They remain not_run pending target-device evidence.
- The current Python 3.11 build baseline supports Windows 8.1/version 6.3 or newer. Windows 8.0/version 6.2 must be blocked by preflight. The target-device release gate is not complete until a supported target is tested.
