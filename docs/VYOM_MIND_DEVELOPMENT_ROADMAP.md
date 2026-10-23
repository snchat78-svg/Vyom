# Vyom Mind Development Roadmap

## Goal

Build a general-purpose desktop assistant that interprets meaning rather than depending on exact command strings. Voice and typed input must share the same intent, planning, execution, verification, and response pipeline. App and file names come from runtime discovery or user input, not a growing hard-coded alias catalogue.

This roadmap is incremental. Each phase ships tests and an explicit acceptance gate; a phase is not complete merely because its module exists.

## M0 — Baseline and observable contracts

**Purpose:** Make failures diagnosable before adding more intelligence.

- Preserve raw transcript, recognized/normalized text, language/session context, chosen intent, confidence, planned steps, observations, verification and final response.
- Use the same goal compiler, capability registry, result schema and context owner across voice and text paths.
- Keep logs bounded and redact sensitive content.
- **Gate:** regression suite proves voice/text enter the same executor and that a dispatched action cannot be reported as verified success without evidence.

**Status:** Existing Phase 1–5 work is in the repository; end-to-end acceptance still requires testing on the user's Windows PC.
**M0.1 progress:** Voice metadata now carries the raw STT transcript, normalized Roman command, recognizer language/status, command-normalizer confidence and bounded correction records into the shared ConversationManager. Each bounded in-memory conversation turn returns a structured trace containing source, input surfaces, corrections, execution status/stage, duration and explicit verification status. Generic execution success is not treated as verified unless verification evidence is present. This trace is in-memory only in this phase; disk-persistent raw-transcript logging is deliberately not added.

**M0.2 progress:** Each conversation turn now has a unique trace ID and receives compact IntentEngine and GoalRouter telemetry through an optional trace sink. The trace correlates intent type, target-presence (not target content), selected route, summarized goal compilation, mission state/progress/replay lock and presence-only session context. Plan arguments, goal text, target names, file paths and context values are deliberately excluded from these summaries. Legacy custom executors remain supported without being passed unsupported keywords. CI tests cover the real executor intent/route handoff and verify that synthetic private plan/context values do not appear in the compact trace.

**M0.3 progress:** Reuses the existing M4 WorldState observation history and M5/M6 verification outputs; it does not add another observer or verifier. The shared executor wrapper correlates only observations timestamped during the current command turn into the same trace ID. Each event contains the phase/time, compact result state, and explicit verification state/level where reported; action IDs, target/window/control names, payloads, observation reasons and full world snapshots are excluded. A turn with no new observation reports `no_new_observations`, not fabricated evidence. Regression tests cover stale-turn exclusion, correlation, payload redaction and absent observations.

**M0.4 progress:** The entry point now creates one ConversationManager and injects that exact instance into VoiceController; typed input calls `process_text` on the same manager rather than bypassing it to call the executor directly. This closes the M0.1 trace gap for typed turns while preserving the existing CommandParser and executor boundary. `tests/test_m0_4_shared_frontend.py` guards manager identity, text routing and absence of direct executor calls from the desktop text path. CI run 39400224264 passed 300 tests and 12 subtests and built/verified the Windows EXE. The remaining platform acceptance is real interactive Windows/microphone validation.

**M0 exit-gate audit — automated gate passed:** Commit `b92d277ebdb5a9bb49469612e4388b1979ff044c` passed [CI run 39401980752](https://github.com/snchat78-svg/Vyom/actions/runs/39401980752) for the exact SHA. The audit found mission traces summarized counts and state but did not preserve plan topology. The trace now includes at most 16 payload-free step summaries (position, allowlisted step type, sanitized status, dependency count, and pre/postcondition presence) plus an explicit truncation flag; IDs, action/target text, arguments, and condition contents are excluded. Regression tests exercise typed and voice turns through one injected executor and check that generic executor success without verification remains `not_reported`. The full test suite, Windows EXE build, EXE verification, and artifact upload all passed. Real Windows/microphone/cross-app validation remains external and pending.





## M1 — Noisy speech recovery

**Purpose:** Recover likely command intent when STT misspells operation words or a target name.

- Only repair command-boundary operation markers using a generic grammar vocabulary.
- Correct target names only from runtime/context-supplied candidates and only when the score and margin are sufficiently clear.
- Keep the original transcript and every correction in the result for diagnostics.
- Never rewrite arbitrary text that the user intends to type or search for.
- Ambiguous matches remain unresolved and must be clarified, not guessed.
- **Gate:** misspelled leading/trailing operation tokens recover; dynamic target candidate can recover a clear typo; tied candidates remain unchanged and require clarification; user payload remains unchanged.

**M1 payload preservation — automated gate passed:** Commit `144909deaf50575b3b999337c895ab237d355c23` passed exact-SHA [CI run 39403055826](https://github.com/snchat78-svg/Vyom/actions/runs/39403055826); the full suite and Windows EXE verification/upload passed. The normalizer now protects target/payload suffixes while still normalizing a later compound-command segment.

**M1 confidence-margin audit — automated gate passed:** Commit `c87d406f3057a0497e6943301fe849b41ea6bf68` passed exact-SHA [CI run 39404026850](https://github.com/snchat78-svg/Vyom/actions/runs/39404026850). The fast-return bypass is closed: both quick search and targeted Program Files discovery now apply the score-margin rule before selecting a single candidate, and near-tied candidates are kept together for explicit selection. Regression tests cover a close runner-up just below the old strong-score cutoff, a clear winning margin, and a close targeted-discovery candidate.

**M1 direct AppsFolder ambiguity audit — automated gate passed:** Commit `3f0b172edc5f3d69737da0eff4ad2ed97521b3f0` passed exact-SHA [CI run 39404982337](https://github.com/snchat78-svg/Vyom/actions/runs/39404982337). The fallback enumerates exact matches without launching during discovery; a unique match can launch, while duplicates return a selection response with disambiguating AppsFolder identifiers. A test-fixture/parser escape mismatch was fixed so Python now parses the real PowerShell tab-delimited record contract. The suite verifies that ties never trigger a launch and unique matches still launch.

**M1 final acceptance matrix — implementation awaiting CI:** Dedicated tests now cover a clear runtime candidate correcting a target typo while preserving the raw transcript; tied runtime candidates leave the target unchanged and expose ambiguity; and the semantic route converts that ambiguity into a clarification response with an empty plan. M1 is not marked complete until exact-SHA CI passes these tests. Real microphone/accent testing on Windows remains external validation.

## M2 — Meaning and intent hypotheses

- Separate task intent from entities, target, payload, constraints, references, and desired result.
- Score multiple plausible interpretations with context; expose alternatives when scores are close.
- Use correction history only when user-approved and scoped to that user/device.
- Do not execute low-confidence guesses.
- **Gate:** paraphrases and noisy transcripts resolve to the same structured goal; ambiguity reliably asks a concise question.

**Current implementation:** `ai_core/meaning_intent_engine.py` derives a provider-independent meaning frame from the existing action plan (intent, targets, payloads, constraints, references, desired result and competing hypotheses). It does not replace the existing execution/planning route. Close runtime-target candidates force a clarification and an empty plan rather than dispatching a guessed target.

**M1 automated gate passed:** Commit `6a7054de0828949f1f1bcade33a06cb9438fa192` passed exact-SHA [CI run 39405455918](https://github.com/snchat78-svg/Vyom/actions/runs/39405455918), including clear runtime typo recovery with raw transcript retention, tied-target ambiguity and an empty plan at the semantic dispatch boundary. M1's real microphone/accent benchmark and interactive Windows behavior remain external validation.

**M2 UI target preservation — CI verified:** Commit `d40edb47ebc0be055c7a3b337661e70dcf80f11a` passed exact-SHA [CI run 39405929075](https://github.com/snchat78-svg/Vyom/actions/runs/39405929075). The meaning frame preserves explicit non-placeholder targets such as `click Save`; tests cover payload/constraint separation, competing alternatives and paraphrase parity.

**M2 correction-history safety — policy:** voice/command_normalizer.py uses a fixed alias set and emits bounded corrections for the current turn; normalizing an unknown target does not teach a new alias. Regression coverage confirms a target from one turn remains unchanged in a later turn. No persistent correction learning is enabled. Any future learning must be explicitly user-approved and scoped to that user/device, and belongs to the opt-in M9 memory gate.

**M2 confidence/hypothesis matrix — CI verified:** Commit `d0dd7910c32169f1884759254e47b969c38429c8` passed exact-SHA [CI run 39415383368](https://github.com/snchat78-svg/Vyom/actions/runs/39415383368): full tests, syntax/import checks, Windows EXE build and verification, and artifact upload. A configurable confidence floor (default 0.65) keeps low-confidence or malformed-confidence action frames unresolved instead of marking the hypothesis selected. A shared dispatch-boundary gate converts low-confidence executable capability/mission plans or tied runtime target candidates into terminal clarification and an empty plan. Commit `74c6ec0c5f0baafd40272bf32342ee00d0dbc268` passed exact-SHA [CI run 39416145129](https://github.com/snchat78-svg/Vyom/actions/runs/39416145129): full tests, syntax/import checks, Windows EXE build/verification and artifact upload. A deeper routing audit found and fixed a plan-precedence bypass: ReasoningEngine could reuse a precompiled contextual/model plan after semantic clarification. Terminal conversation/clarification routes now outrank all plan candidates, and create_plan returns no steps for terminal routes even if stale plans remain in analysis. Commit `d1001544bd50dd308fe7293132aa4c72be2b0e2e` passed exact-SHA [CI run 39417115798](https://github.com/snchat78-svg/Vyom/actions/runs/39417115798): full tests, syntax/import checks, Windows EXE build/verification, and artifact upload. The M2 automated route/normalization gates are green; real microphone, accent, and desktop validation remain external.

## M3 — Complex goal decomposition and planning

- Convert compound requests into ordered steps with dependencies, preconditions, postconditions and a completion criterion.
- Identify missing details, irreversible effects and steps requiring confirmation before acting.
- Keep the plan generic; app names and controls are runtime entities.
- **Gate:** compound workflows preserve ordering and do not execute dependent steps after a failed prerequisite.

**Current implementation:** `ai_core/mission_planner.py` validates the complete mixed legacy/generic dependency graph. `ai_core/mission_runtime.py` independently rejects malformed plans at mission start/re-plan, resets caller-supplied completion claims, and allows step completion only when postconditions are verified. Re-planning carries forward only verified steps. Validation remains data-driven.

**M3 pre-dispatch confirmation — automated gate verified:** `ActionRiskPolicy` checks action semantics, target labels and structured risk metadata for common destructive/external side effects while deliberately ignoring free-form typed payload text. Before `MissionRuntime.start`, any flagged plan is held in-session and no step runs until the user sends an explicit `confirm action` or `cancel action`; unrelated commands cannot bypass the pending gate. Risk fields are preserved by the generic action schema. Commit `7e7cdd4aa604b6e71b3fdc0532f8a336ce5781d2` passed exact-SHA [CI run 39418664644](https://github.com/snchat78-svg/Vyom/actions/runs/39418664644), including the complete test suite, Python syntax/import checks, Windows EXE build, verification and artifact upload. The classifier is conservative and pattern-based, not a guarantee that every app-specific side effect can be inferred. English, Roman Hindi/Hinglish and common Devanagari risk labels are covered; unknown application semantics still need dedicated metadata or policy. Pending approvals are session-scoped and not resumed after process restart; no action is auto-executed on restart.

**Status:** Devanagari destructive/financial labels, Unicode-safe phrase boundaries, safe keyboard/Save actions, and typed-payload isolation passed exact-SHA [CI run 39420557346](https://github.com/snchat78-svg/Vyom/actions/runs/39420557346). Expanded account/subscription/order/access/token/publication risk coverage passed exact-SHA [CI run 39427132026](https://github.com/snchat78-svg/Vyom/actions/runs/39427132026). The failed-prerequisite integration guard passed the full test suite and Windows EXE build/verification/upload on exact commit `7a83b53186017645ce73bc9a277b3faa6107a6a0` in [CI run 39608106621](https://github.com/snchat78-svg/Vyom/actions/runs/39608106621). M3's automated gates are green; provider-specific semantics and real Windows multi-step acceptance remain external validation.

## M4 — Live world state and contextual reference resolution

- Build fresh snapshots of active window, focused/selected control, visible UIA elements, running windows, clipboard only when needed, and the latest verified task state.
- Resolve references such as "in it", "that window", "same file", and follow-ups against recent observed state.
- Give observations timestamps and bounded history; observer failure must not stop listening.
- **Gate:** stale/ambiguous references are clarified; latest observations survive retry and re-planning.

**M4.1 progress:** UIA snapshots now include a bounded list of visible top-level windows; recorded observations retain timestamps in bounded history; the autonomous loop does not read clipboard contents unless explicitly requested; contextual text entry from a runtime snapshot requires fresh UIA focus evidence instead of trusting a stale session application label.

**M4.2 progress:** Generic references such as “it”, “that window” and “same file” resolve only when a fresh runtime snapshot supports one unambiguous target. Conflicting focus/selection, stale observations, unavailable UIA state, or an active-window title that does not confirm the current file now produce a clarification instead of an ungrounded action.

**M4.3 progress:** Session current-app/current-file/current-target context is no longer updated from a proposed intent before execution. Legacy context is committed only after ObservationVerifier confirms the action; failed execution or verification preserves the last verified context.

**M4.4 progress:** Observation history now stores compact target/verification summaries instead of full nested world snapshots. The newest observation is attached to the same snapshot passed into re-planning, avoiding a second inconsistent UIA read; if the fresh snapshot cannot be produced, re-planning stops instead of using stale state.

**M4.5 progress:** Contextual references now use focus, selection and active-window fields from the same nested UI observation as their canonical source. When a nested UI timestamp is present, it must also be fresh; a recent outer world snapshot cannot disguise stale UI data. Regression tests cover changed active windows, conflicting mirrored focus/selection, missing live focus and stale nested UI timestamps.

**M4.6 progress:** Re-planning now validates that the captured world snapshot is recent, finite and not future-dated beyond a small clock-skew allowance. If a nested UI timestamp exists, it is validated separately so a fresh outer timestamp cannot hide stale UI state. Missing, stale or failed observations stop re-planning before the reasoning provider is called; regression tests cover old/future/error snapshots and the no-reasoning-on-stale-state path.

**M4.7 integration contract — tests added; CI pending:** New regression tests pass the actual `WorldStateModel.snapshot()` schema into `ContextActionCompiler` using a controlled UI observer. A coherent fresh focus/selection resolves “click it” to the live target, while stale nested UI evidence is rejected even when the outer world snapshot is fresh. This bridges the existing components without duplicating their logic; interactive Windows focus/window validation remains pending.

**M4.8 clipboard privacy default — implementation + tests added; CI pending:** `WorldStateModel.snapshot()` no longer reads clipboard contents by default. Callers must explicitly pass `include_clipboard=True` when clipboard content is required for the task; existing autonomous observations already opt out by default. Tests preserve explicit clipboard reads while guarding that default snapshots only return a skipped marker. This is a privacy-by-default boundary and does not inspect or clear clipboard data.

**M4.9 coherent foreground observation — implementation + tests added; CI pending:** UIStateObserver now compares active-window identity before and after collecting focus/selection/tree data. A foreground switch or insufficient identity evidence marks the snapshot `coherent=False`; ContextActionCompiler refuses contextual-reference resolution from such a snapshot and asks for clarification. Legacy/custom observers with no coherence field remain compatible. This prevents a single context snapshot from silently combining controls across windows; exact-SHA CI and real Windows foreground-switch testing remain pending.

**M4.10 re-planning coherence gate — implementation + tests added; CI pending:** AutonomousAgent's shared world-observation freshness validator now rejects UI snapshots explicitly marked `coherent=False`, even when outer and nested timestamps are fresh. Re-planning stops before calling the reasoning provider on mixed-window evidence. Legacy UI providers without a coherence field retain timestamp-based compatibility; exact-SHA CI is pending.

**M4.11 live-UI re-planning gate — implementation + tests added; CI pending:** The re-planning boundary now requires the current snapshot to contain `ui.available=True`; a recent outer timestamp cannot mask omitted or explicitly unavailable UI evidence. The generic freshness helper remains backward-compatible for summary-only callers, while mission re-planning opts into the stricter live-UI contract. Tests cover missing/unavailable UI and prove the reasoning provider is not called. Exact-SHA CI and actual Windows UIA validation remain pending.

**M4.12 live-UI timestamp gate — CI verified:** When the strict mission re-planning path is active, a UI payload must have a valid, fresh capture timestamp as well as `available=True`. A fresh outer world timestamp or a bare UI availability flag cannot substitute for recent live evidence. Legacy callers that do not opt into the strict contract retain timestamp-optional compatibility. Tests reject missing and stale nested UI timestamps. The combined M4.7–M4.12 acceptance passed exact SHA `57b43cfd52f5ef6c95c150257165e640be22e101` in [CI run 39615193598](https://github.com/snchat78-svg/Vyom/actions/runs/39615193598); real Windows UIA validation remains pending.

**Status:** M4 remains in progress. Automated tests cover compact history, single-snapshot re-planning, reference freshness, ambiguity, and verified-only context updates. Real desktop focus/window behavior still requires end-to-end validation on Windows.

## M5 — Generic action grounding

- Rank visible UI Automation candidates using live Name, AutomationId, ControlType, class, window identity and available control patterns.
- Use Invoke/Value/Selection/Toggle/Focus before coordinate clicks when supported.
- Treat app and file names as runtime data and avoid app-specific action lists.
- **M5.1 progress:** Grounding excludes hidden/disabled controls from action selection, treats ControlType/ClassName as filters rather than unique identities, rejects near-tied candidates even when structural filters are present, and normalizes invalid/non-finite scores without crashing. Tests cover near ties, hidden/disabled targets and malformed confidence.
- **M5.2 progress:** The selected operation is determined from the live element's callable UIA wrapper methods before dispatch. Explicit invoke requires the Invoke operation and cannot silently fall back to a generic click; ordinary click prefers semantic methods before lower-level input fallback. Grounding reports supported operations, dispatch results record the chosen method, and unsupported patterns fail before acting.
- **M5.3 progress:** Semantic targets are grounded once and the same UIA element wrapper is used for the pre-action observation, dispatch and post-action observation. Before dispatch, live target identity and (when available) its parent-window identity must match the observation; missing/hidden/disabled targets, unavailable observation, or a changed active window stop the action. Postcondition checks now fail closed when fields, target-existence evidence, or usable before/after UI-tree snapshots are missing. A post-action observer error or unavailable snapshot downgrades the action result to failure instead of reporting success. Regression tests cover changed targets/windows, exact element reuse, empty observation trees, missing negative-check evidence and missing execution results.
- **M5.4 progress:** Semantic postconditions are now operation-specific: typing requires the focused control's observed value/text to change and contain the requested payload, with a narrow fallback for explicitly absent focus only when the payload newly appears in a changed visible UI surface (an unrelated UI-tree change is insufficient); ValuePattern requires exact equality and supports verifying a deliberate clear (including preserving the empty value in UIA observation); toggling requires toggle_state or selection state to change rather than a label-only change. set_ui_value also reuses the exact prepared grounded element rather than performing a second independent grounding. Regression tests cover false-positive text entry, exact/empty values, toggle-state changes and single-element dispatch.
- **M5.5 progress:** Failure outcomes now carry a provider-independent recovery classification. Only explicit pre-dispatch failures use the existing bounded retry after a fresh observation. Ambiguous targets request user clarification; unsupported operations stop without repetition; post-dispatch verification failures and unknown outcomes stop rather than blindly replaying a potentially completed side effect. The classification is saved in mission history and returned to the caller. Existing direct callers of MissionRuntime.mark_failed retain the legacy retry default unless they opt into the new policy.
- **M5.6 progress — coherence-aware dispatch and verification; CI verified:** `WindowsUICapability` refuses semantic target dispatch when the pre-action observer explicitly marks its snapshot incoherent, and an incoherent post-action snapshot is treated as unverified failure. Legacy observers that omit the coherence field remain compatible. Exact-SHA CI for the combined M5.6–M5.7 acceptance passed on commit `b7f566773ee23139fdd507e19b19588d8c587c33` in [run 39719715495](https://github.com/snchat78-svg/Vyom/actions/runs/39719715495), including the full test suite and Windows EXE build/verification/upload. The gate applies only to semantically grounded element-target actions; coordinate and legacy action paths retain their existing contracts.
- **M5.7 progress — timestamp-fresh semantic UI boundary; automated gate passed:** Semantic target actions require a finite, recent capture timestamp (maximum age 10 seconds, future clock skew up to 2 seconds) on both pre-action and post-action UI snapshots. Missing/stale pre-action evidence blocks dispatch; stale post-action evidence turns the result into an unverified failure. Regression tests reject NaN/infinite, boolean, non-numeric, stale and overly future-dated timestamps. Exact-SHA CI passed in [run 39719715495](https://github.com/snchat78-svg/Vyom/actions/runs/39719715495) for `b7f566773ee23139fdd507e19b19588d8c587c33`; real Windows UIA testing remains external.
- **Gate:** M5.3–M5.7 automated guards passed the full CI/EXE pipeline, but different labels/layouts and foreground/window-change scenarios still require interactive Windows testing.

## M6 — Execute, verify, recover

- Execute one validated action at a time and verify its actual postcondition.
- After a failure, refresh observation, classify the failure, and retry/re-plan only within a strict budget.
- Never repeat completed side effects during re-planning.
- **Gate:** delayed effects, absent observers, wrong foreground windows and failed steps end in verified recovery or honest failure.
- **M6.1 progress:** Every failed step now captures a dedicated post-failure observation. A bounded retry is scheduled only for an explicit pre-dispatch rejection and only if the newly captured UI observation is available and the outer/UI timestamps pass freshness checks; stale/missing observation blocks the mission before retry is queued. Failure responses include a compact recovery summary (window/control identity only), not observed text/value payloads. Potentially completed or unknown side effects still stop without automatic replay.
- **M6.2 progress:** MissionRuntime now enforces a replay lock for uncertain/unknown post-dispatch outcomes. A new model plan cannot override the lock, and ordinary unblock attempts are rejected. Clearing it requires an explicit replay-authorization flag after the user/operator has checked the current state; only a SHA-256 fingerprint and step metadata are retained, not the action payload. Tests cover rejected model re-plans, no implicit unblock, and the explicit authorization path.
- **M6.3 progress:** The conversation/executor boundary now intercepts all input while an uncertain-action replay lock is active. Bare yes/no and unrelated commands cannot bypass it. The user can say the action already happened (stop without replay), explicitly say it did not happen and request retry (only after a fresh live UI observation), or cancel recovery. The replay lock cannot be cleared by starting another mission; conversation results expose a dedicated `needs_confirmation` status. The continuation loop uses the same failure classifier and recovery observation gate as the initial loop.
- **M6.4 progress:** Added end-to-end executor-boundary tests for lock interception, cancel-without-replay, retry blocked by unavailable UI observation, confirmed retry followed by verified completion, and retry followed by failed verification. Runtime now installs a replay lock immediately when an executor claims success but the postcondition is not verified; the initial and continuation loops both return to recovery confirmation instead of allowing a new plan or claiming success.

**M6.5 progress:** Added a local per-user atomic recovery journal configured by the desktop entry point. It persists only the active marker, outcome category, SHA-256 fingerprint and timestamp—never action text, target, arguments or the mission plan. On restart, the unresolved marker restores a blocker before normal command routing; the old plan is intentionally unavailable, so automatic retry is prohibited. Invalid/unreadable journals fail closed, and explicit cancellation/user confirmation clears the marker. This is best-effort filesystem persistence, not a guarantee against disk loss or forced termination during the write; the journal status is exposed in the mission snapshot.

**M6.6 progress:** Hardened recovery-journal discovery so only a definite FileNotFoundError is treated as a missing marker. Permission/stat errors now restore an in-memory blocker and return read_failed rather than treating the marker as absent. Regression coverage simulates an inaccessible journal path and confirms a new mission remains blocked without retaining an executable plan.

## M7 — Web research and source-grounded answers

- Use configurable search/retrieval providers and public-source fetchers with URL safety, timeouts, page limits, and source attribution.
- Distinguish source facts, inference, conflicting reports and unknowns.
- Treat web content as untrusted data; never follow instructions embedded in a page as commands to the desktop.
- **Gate:** relevant source links accompany supported answers; unavailable/weak sources produce an honest limitation instead of fabricated facts.

**M7.1 progress — public-source boundary and evidence contract; automated gate passed:** Public retrieval now rejects redirects to URL targets disallowed by the public-URL validator, caps each response body at 1 MB (with a lower configurable limit), rejects search snippets without a safe public citation, and validates returned source links. Sourced results explicitly label the evidence type and report one source, no model inference, unverified independent corroboration, and untrusted source content. Empty/failed lookup returns `answer_status=unknown`, no source, and no invented answer. Regression tests cover explicit localhost/private-IP/file redirects, the response byte cap, source metadata, and unknown results. Exact-SHA CI passed on `09a59277a978d645292ecf4892e45e24cd24d99a` in [run 39720196175](https://github.com/snchat78-svg/Vyom/actions/runs/39720196175), including the full test suite and Windows EXE build/verification/upload.

**M7.2 progress — multi-source evidence comparison; automated gate passed:** Retrieval continues through bounded query/source attempts, retains one cited excerpt per distinct hostname, and compares Unicode-aware sentence context. Close textual overlap is labelled `textually_aligned`; different numeric/date-like values in highly overlapping contexts yield `potential_numeric_conflict` and an unresolved warning; other disagreements remain `divergent_unresolved`. Same-host pages are deduplicated, and hostname count is not treated as publisher independence. Four deterministic cross-source tests plus the legacy singular-source compatibility test are covered. Exact-SHA CI passed on `aa744d7261200de32c897829158ef585d6b2308b` in [run 39730872062](https://github.com/snchat78-svg/Vyom/actions/runs/39730872062), including the Windows EXE workflow.

**M7.3 progress — DNS-aware public destination preflight; automated gate passed:** Before a real network fetch, Vyom resolves the target hostname and rejects DNS failures, empty answers, or any answer set containing a non-global address. Redirect destinations use the same fail-closed check. Exact-SHA CI passed on `72815257ca2f7deb89a82b86bee17c904536414a` in [run 39741822185](https://github.com/snchat78-svg/Vyom/actions/runs/39741822185). This preflight alone still had a DNS time-of-check/time-of-use gap; M7.4 closes that gap at the actual HTTP/HTTPS socket.


**M7.4 progress — transport-level DNS pinning; automated gate passed:** Public HTTP and HTTPS handlers now resolve the origin at connection time, reject failed/empty/malformed resolution and any non-global address, and connect directly to a validated numeric sockaddr from that exact DNS answer set rather than re-resolving the hostname during TCP connect. HTTPS retains the original hostname for SNI and certificate hostname validation; the Host authority remains hostname-based. Redirects are rechecked, ambient environment proxies are disabled for this fetch path, and malformed DNS iterables fail closed without attempting a second resolver call. Deterministic regression tests cover the pinned numeric socket address, mixed public/private DNS, malformed DNS output, original TLS hostname, and proxy/opener policy. Exact-SHA CI passed on `f417bebeecd902bbfe1111bbad623eaaaeceb4a0` in [run 39746025751](https://github.com/snchat78-svg/Vyom/actions/runs/39746025751): 364 tests and 28 subtests passed, followed by Windows EXE build/verification and artifact upload. External live-network/TLS validation remains outside CI.

**M7.5 progress — configurable bounded retrieval providers; automated gate passed:** Introduced `RetrievalProvider(name, retrieve, max_results=3)` with callback signature `(client, query_variants, preferred_language)`. Built-in Wikipedia and DuckDuckGo retrieval use the same contract, and configured providers can be injected for local integrations/tests. Public citation validation, `client.fetch_text()` network boundary, response bytes/timeouts/overall deadline, unknown-on-failure, and legacy singular `source` compatibility are preserved. Provider count is capped at 4, accepted results at 3/provider and 6/lookup, fetches at 6/provider and 12 total, excerpts at 1,200 characters, URLs at 2,048 characters, titles at 240, sites at 160 and answers at 2,400. Tests cover provider ordering/failure, unsafe citations, normalized-host dedupe, malformed outputs, empty configuration, output limits, provider-count cap and network-fetch budget. Exact-SHA CI passed on `90ae4ead63c586b8da98191d5266254736c5269d` in [run 39753595589](https://github.com/snchat78-svg/Vyom/actions/runs/39753595589): 373 tests and 28 subtests passed; Windows EXE build/verification/upload succeeded. Limitation: custom provider callbacks are trusted local code rather than a sandbox and must use `client.fetch_text()` for the transport safety/limits.

**M7 automated acceptance — passed:** M7.1–M7.7 and the combined acceptance audit passed. Exact-SHA audit CI on `59b8880d0c63d359c681615a77e53ee5c917d255` in [run 39786556563](https://github.com/snchat78-svg/Vyom/actions/runs/39786556563) passed 387 tests and 30 subtests, tracked Python syntax checks, core/voice imports, clean build, Windows EXE verification and artifact upload. Two added end-to-end tests ensure weak/future-dated quality metadata cannot suppress numeric or semantic conflicts, and copied cross-host excerpts do not establish independent corroboration. External live network/TLS and real Windows/microphone behavior remain unverified. **Next: M8 general reasoning and sourced-answer evaluation; not started.**

**M7.6 progress — broader semantic contradiction detection; automated gate passed:** Added context-gated polarity/opposition rules for selected non-numeric opposing claims plus a shared-context negation check. Numeric/date conflicts retain precedence. The new `potential_semantic_conflict` relation returns `answer_status=conflicting_sources`; the answer tells the user the claims are unresolved and explicitly does not decide which source is correct. Coverage includes open/closed, permitted/prohibited paraphrase, true/false-family cues, negation, unrelated claims, compatible but differently worded claims, Hindi open/closed and the end-to-end unresolved response. A first run found that Hindi cue matching/anchor overlap needed the original sentence rather than Unicode word tokens alone; this was corrected and tested. Exact-SHA CI passed on `6d5101f10a2c35d2f2bf2699d2960db861f6dfd9` in [run 39757311244](https://github.com/snchat78-svg/Vyom/actions/runs/39757311244): 380 tests and 28 subtests passed; Windows EXE build/verification/upload succeeded. Limitation: this bounded rule set is not general semantic understanding; implicit, low-overlap, unlisted antonym and nuanced multilingual contradictions may remain unresolved.

**M7.7 progress — source-quality evaluation; automated gate passed:** The source-normalization contract preserves explicit publication dates, authors and publishers. Per-source scoring covers freshness (unknown dates stay unknown), excerpt sufficiency/boilerplate, attribution, specificity and duplicate/repost signals within the current retrieved set. Scores do not use raw source count or textual alignment as truth points; they are metadata quality signals, not probabilities of truth or proof of publisher independence. Weak/very-short primary evidence returns `answer_status=unknown` while retaining citations; numeric/semantic conflict outcomes retain precedence. Deterministic tests cover fresh/stale/unknown dates, duplicate/repost detection, unrelated-source count neutrality, weak-excerpt unknown handling and date preservation. Exact-SHA CI passed on `98d7855c83b35cc37dadc01c4245c3803219394f` in [run 39785293786](https://github.com/snchat78-svg/Vyom/actions/runs/39785293786): 385 tests and 28 subtests passed; syntax/import checks, clean build, Windows EXE verification and artifact upload passed. **Next:** combined M7 audit; do not start M8 until that gate passes.

## M8 — General conversation and reasoning
**Status: COMPLETED — automated acceptance gate passed on 2026-10-23.**

Exact tested code/test commit: `0253010a1df4837a926631a63ad27042ce1f0d87`. [GitHub Actions run 39899815866](https://github.com/snchat78-svg/Vyom/actions/runs/39899815866) passed **395 tests and 30 subtests**, Python syntax checks, core/voice imports, clean build, Windows EXE build/verification, and `Vyom_EXE` artifact upload.

- Existing configurable reasoning providers and local/remote gateway stay behind the model-independent execution/result contracts; model output remains data and does not directly execute generated code.
- M8 hardens response epistemics: `conflicting_sources` remains unresolved even if an adapter incorrectly sets `success=True`; `unknown`/weak evidence cannot be promoted by answer text; source URLs remain visible; inferred results are explicitly labelled as inference; a provider's `known` label is explicitly not described as independent verification.
- Existing provider-fallback tests cover Gemini rate-limit fallback to Local Qwen, provider cooldown, invalid gateway output and offline behavior. New `tests/test_m8_reasoning_evaluation.py` covers Hindi/English conflict handling, status precedence, citations, sourced/inferred/known/unknown outcomes, provider exceptions and deterministic fallback.
- Common safe desktop command paths remain deterministic; the response model stays opt-in. A failed conversational reasoning provider does not imply a desktop action failed or succeeded.
- Limitations: a provider-supplied status is metadata, not proof; heuristic source quality/conflict detection remains bounded; external network/TLS and the user's actual Windows desktop/microphone were not exercised by GitHub CI.

**M8 gate:** passed. Do not restart M8 unless a new requirement or regression is recorded. **Next: M9.1 — Opt-in learning baseline and memory-schema inventory.**

## M9 — Personalization and safe learning
**Status: M9.1–M9.5 completed on exact-SHA CI. Consent remains default-off and session-only.**

### M9.1 — Baseline inventory and memory schema (COMPLETED)
- Delivered the memory/persistence inventory, design-only schema and deterministic baseline tests.
- **Gate passed:** [run 39900778509](https://github.com/snchat78-svg/Vyom/actions/runs/39900778509): 399 tests + 30 subtests; syntax/import, clean build and EXE verification/upload passed.

### M9.2 — Explicit opt-in and approval (COMPLETED)
- Typed-text CLI supports session-only `memory consent status/on/off`, pending review and separate per-record approval. Consent defaults OFF.
- **Gate passed:** [run 39901852967](https://github.com/snchat78-svg/Vyom/actions/runs/39901852967): 408 tests + 30 subtests, syntax/import, clean build and EXE verification/upload passed.

### M9.3 — Versioned storage and provenance (COMPLETED)
- `ai_core/user_memory_store.py` provides a per-user schema-v1 JSON envelope, strict record validation, 256-record/1 MB caps, atomic temp-write/fsync/replace and fail-closed behavior for corrupt, oversized or unsupported stores.
- Explicit typed flow: opt in → propose correction/preference → inspect pending candidate → approve that candidate → explicitly save. No automatic voice-transcript learning is connected.
- Reads require current consent and active, unexpired, approved records; saves require current consent and the unchanged in-process approved record.
- **Gate passed:** exact-SHA [run 39906002229](https://github.com/snchat78-svg/Vyom/actions/runs/39906002229) on `de32220023fca744089edcd0311a0d2234a4daae`: **419 tests + 30 subtests**, Python syntax/core/voice imports, clean build, Windows EXE verification and artifact upload.
- **Boundary:** opt-out blocks use but does not erase saved records. The current CLI does not yet provide record inspection/export/deletion.

### M9.4 — Review, export and deletion (COMPLETED)
- Implemented `memory list`, `memory inspect <memory-id>`, `memory export <absolute-path.json>`, `memory delete <memory-id>` and `memory delete all`.
- Review/export require current consent; deletion remains available after opt-out. Export writes only to a new absolute JSON path, excludes expired/inactive records, refuses overwrites and verifies the output. Deletion verifies durable file state; corrupt stores fail closed.
- **Gate passed:** exact-SHA [run 39908005080](https://github.com/snchat78-svg/Vyom/actions/runs/39908005080) on `eb9707498708f1e92bf5ebdf92f491642db95cdf`: 427 tests + 30 subtests; syntax/import, clean build, Windows EXE verification/upload all passed.

### M9.5 — Safe learning integration and exit audit (COMPLETED)
- Only allow-listed presentation preferences and enumerated values are exposed as advisory reasoning-context hints. Correction records, workflow summaries and arbitrary or conflicting values are not injected.
- Read failures supply no hints; current consent, active lifecycle, approval, scope, confidence, provenance and expiry checks are retained. Memory cannot authorize a capability, change the current goal, bypass confirmation or fabricate success.
- **M9 gate passed:** exact-SHA [run 39912869937](https://github.com/snchat78-svg/Vyom/actions/runs/39912869937) on `6f9a99e05555c8c25ac6bcb546934aa6f61d1afc`: 436 tests + 30 subtests; syntax/import, clean build, Windows EXE verification/upload.
- **Limit:** real Windows desktop/audio and live network acceptance remains under M10.4; memory hints are advisory and may not affect the deterministic local path.

## M10 — Release evaluation (cross-cutting; final gate remains after M9)
### M10.1 — Representative benchmark corpus (COMPLETED)
- **Current deliverables:** `tests/fixtures/m10_1_vyom_benchmark_corpus.json`, `tests/test_m10_1_benchmark_corpus.py`, and `docs/VYOM_M10_BENCHMARK_PROTOCOL.md`.
- 15 synthetic contract-only scenarios cover English, Hindi, Roman Hindi, Hinglish, noisy STT, ambiguity, compound-task dependencies, web-grounded/sourced-or-unknown outcomes, conflicting sources, provider outage, uncertain recovery, post-action verification and memory-safety boundaries.
- Each case declares preconditions, expected outcome, required invariants and prohibited outcomes. The first gate validates corpus quality and privacy; it does not claim measured accuracy.
- Keep private transcripts, credentials, actual clipboard payloads and user files out of committed fixtures.
- **Gate passed:** exact-SHA [run 39913443550](https://github.com/snchat78-svg/Vyom/actions/runs/39913443550) on `5841279846599e349dedaadd942ce7736e6c82c2`: **440 tests + 30 subtests**, Python syntax/core/voice imports, clean build, Windows EXE build/verification and artifact upload.
- **Boundary:** this is a completeness/contract gate, not a benchmark run. No measured performance result is claimed. **Next: M10.2 reproducible runner and baseline metrics.**

### M10.2 — Reproducible metrics runner and baseline (NEXT; not started)
- Build a deterministic offline runner over M10.1's synthetic contract corpus, using stubbed/adapted component results rather than real web requests, live models, microphone capture or desktop actions.
- Produce a machine-readable JSON report with corpus version, scenario ID, run status (pass/fail/unrun/error), expected outcome, observed outcome, rationale and metric contributions. Never count an unrun scenario as a pass.
- Define denominator rules and sample sizes before calculating intent/interpretation correctness, unsafe-guess rate, action-verification correctness, task completion/recovery, epistemic-status correctness and latency. Exclude or explicitly classify unsupported/unmeasurable scenarios rather than silently dropping them.
- Verify report determinism for fixed inputs; fail closed on unknown scenario IDs/outcomes and malformed runner output.
- **Gate:** exact-SHA CI runs the deterministic slice and validates its JSON report and metric denominators. Only then establish a baseline and begin M10.3 regression thresholds.
### M10.3 — CI regression thresholds
- Run deterministic benchmark slices in CI, report regressions and block release if safety-critical thresholds fail.
- Keep flaky live-network tests separate from deterministic CI; network failure must not cause invented answers.

### M10.4 — Real Windows integration and release exit gate
- Test supported Windows environment, screen/UI grounding, microphone/STT/TTS, provider outages, multi-step commands and verified postconditions.
- Record device/OS/test evidence and limitations. GitHub EXE compilation alone is not device acceptance.
- **M10 gate:** benchmark thresholds pass on CI and representative Windows integration evidence exists. Release only after M9 safety gate and M10.1–M10.4 acceptance.

## Ordered development sequence and anti-skip rule
1. M0 baseline/trace and shared text/voice path.
2. M1 noisy speech recovery.
3. M2 meaning/intent and safe clarification.
4. M3 complex planning.
5. M4 live world state.
6. M5 action grounding.
7. M6 execute/verify/recover.
8. M7.1–M7.7 source retrieval/evidence quality and combined audit — completed.
9. M8 general reasoning/sourced-answer evaluation — automated gate completed on exact-SHA run 39899815866.
10. M9.1–M9.5 safe-learning gates **completed**; M9.5 passed exact-SHA [run 39912869937](https://github.com/snchat78-svg/Vyom/actions/runs/39912869937).
11. M10.1 synthetic representative benchmark corpus **completed** on exact-SHA [run 39913443550](https://github.com/snchat78-svg/Vyom/actions/runs/39913443550). **M10.2 reproducible metrics runner and baseline is next**, then M10.3 CI regression thresholds and M10.4 real Windows integration/release exit. Do not report measured accuracy before M10.2.

At every new chat, read `docs/VYOM_PHASE_STATE.md`, verify the live branch head and latest applicable CI, then work only on the first incomplete item above. Do not skip, restart or mark a phase complete based only on a commit.

## Explicit limitation

No system can guarantee correct interpretation of every possible sentence or badly corrupted audio. Vyom should use context and safe hypotheses to maximize correct recovery, but ask when meaning is ambiguous, report missing model/network capability honestly, and never claim an unverified desktop action succeeded.
