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

## M1 — Noisy speech recovery

**Purpose:** Recover likely command intent when STT misspells operation words or a target name.

- Only repair command-boundary operation markers using a generic grammar vocabulary.
- Correct target names only from runtime/context-supplied candidates and only when the score and margin are sufficiently clear.
- Keep the original transcript and every correction in the result for diagnostics.
- Never rewrite arbitrary text that the user intends to type or search for.
- Ambiguous matches remain unresolved and must be clarified, not guessed.
- **Gate:** misspelled leading/trailing operation tokens recover; dynamic target candidate can recover a clear typo; tied candidates remain unchanged and require clarification; user payload remains unchanged.

**Status:** The recovery unit-test gate is implemented in CI. Real microphone/accent testing on Windows remains necessary.

## M2 — Meaning and intent hypotheses

- Separate task intent from entities, target, payload, constraints, references, and desired result.
- Score multiple plausible interpretations with context; expose alternatives when scores are close.
- Use correction history only when user-approved and scoped to that user/device.
- Do not execute low-confidence guesses.
- **Gate:** paraphrases and noisy transcripts resolve to the same structured goal; ambiguity reliably asks a concise question.

**Current implementation:** `ai_core/meaning_intent_engine.py` derives a provider-independent meaning frame from the existing action plan (intent, targets, payloads, constraints, references, desired result and competing hypotheses). It does not replace the existing execution/planning route. Close runtime-target candidates force a clarification and an empty plan rather than dispatching a guessed target.

**Status:** Foundation implemented; CI and regression tests are the current acceptance gate. Windows end-to-end behavior remains unverified until tested with the user's microphone and desktop.

## M3 — Complex goal decomposition and planning

- Convert compound requests into ordered steps with dependencies, preconditions, postconditions and a completion criterion.
- Identify missing details, irreversible effects and steps requiring confirmation before acting.
- Keep the plan generic; app names and controls are runtime entities.
- **Gate:** compound workflows preserve ordering and do not execute dependent steps after a failed prerequisite.

**Current implementation:** `ai_core/mission_planner.py` validates the complete mixed legacy/generic dependency graph. `ai_core/mission_runtime.py` now independently rejects malformed plans at mission start/re-plan, resets any caller-supplied completion claims, and allows step completion only when the current step's postcondition is verified. Re-planning carries forward only previously verified steps. Validation remains data-driven and adds no action-name allowlist.

**Status:** CI regression coverage added for malformed plans, dependency cycles, unverified completion and untrusted re-plan status. Real Windows multi-step scenarios still require desktop validation.

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

**Status:** M4 remains in progress. Automated tests cover compact history, single-snapshot re-planning, reference freshness, ambiguity, and verified-only context updates. Real desktop focus/window behavior still requires end-to-end validation on Windows.

## M5 — Generic action grounding

- Rank visible UI Automation candidates using live Name, AutomationId, ControlType, class, window identity and available control patterns.
- Use Invoke/Value/Selection/Toggle/Focus before coordinate clicks when supported.
- Treat app and file names as runtime data and avoid app-specific action lists.
- **M5.1 progress:** Grounding excludes hidden/disabled controls from action selection, treats ControlType/ClassName as filters rather than unique identities, rejects near-tied candidates even when structural filters are present, and normalizes invalid/non-finite scores without crashing. Tests cover near ties, hidden/disabled targets and malformed confidence.
- **M5.2 progress:** The selected operation is determined from the live element's callable UIA wrapper methods before dispatch. Explicit invoke requires the Invoke operation and cannot silently fall back to a generic click; ordinary click prefers semantic methods before lower-level input fallback. Grounding reports supported operations, dispatch results record the chosen method, and unsupported patterns fail before acting.
- **M5.3 progress:** Semantic targets are grounded once and the same UIA element wrapper is used for the pre-action observation, dispatch and post-action observation. Before dispatch, live target identity and (when available) its parent-window identity must match the observation; missing/hidden/disabled targets, unavailable observation, or a changed active window stop the action. Postcondition checks now fail closed when fields, target-existence evidence, or usable before/after UI-tree snapshots are missing. A post-action observer error or unavailable snapshot downgrades the action result to failure instead of reporting success. Regression tests cover changed targets/windows, exact element reuse, empty observation trees, missing negative-check evidence and missing execution results.
- **M5.4 progress:** Semantic postconditions are now operation-specific: typing requires the focused control's observed value/text to change and contain the requested payload, with a narrow fallback for explicitly absent focus only when the payload newly appears in a changed visible UI surface (an unrelated UI-tree change is insufficient); ValuePattern requires exact equality and supports verifying a deliberate clear (including preserving the empty value in UIA observation); toggling requires toggle_state or selection state to change rather than a label-only change. set_ui_value also reuses the exact prepared grounded element rather than performing a second independent grounding. Regression tests cover false-positive text entry, exact/empty values, toggle-state changes and single-element dispatch.
- **Gate:** different labels and layouts work through discovered UI properties; close candidates do not trigger unsafe actions. M5.3/M5.4 automated guards are not proof of real desktop compatibility; foreground/window-change scenarios still require interactive Windows testing.

## M6 — Execute, verify, recover

- Execute one validated action at a time and verify its actual postcondition.
- After a failure, refresh observation, classify the failure, and retry/re-plan only within a strict budget.
- Never repeat completed side effects during re-planning.
- **Gate:** delayed effects, absent observers, wrong foreground windows and failed steps end in verified recovery or honest failure.

## M7 — Web research and source-grounded answers

- Use configurable search/retrieval providers and public-source fetchers with URL safety, timeouts, page limits, and source attribution.
- Distinguish source facts, inference, conflicting reports and unknowns.
- Treat web content as untrusted data; never follow instructions embedded in a page as commands to the desktop.
- **Gate:** relevant source links accompany supported answers; unavailable/weak sources produce an honest limitation instead of fabricated facts.

## M8 — General conversation and reasoning

- Support a configurable local/remote model provider for open-domain paraphrases and multi-step reasoning when available.
- Keep deterministic local handling for common safe operations, with a model-independent structured-goal interface.
- If all reasoning providers are unavailable, say so clearly and use only verified local or retrieved knowledge.
- **Gate:** provider outages do not break basic desktop commands or the voice loop; responses distinguish known, sourced, inferred and unknown information.

## M9 — Personalization and safe learning

- Store opt-in, user-approved corrections, preferences and previously verified workflows in versioned local memory.
- Provide provenance, confidence, expiry, export and deletion.
- Generate capability specifications only; validate and test them in isolation, and require explicit approval before enabling new capabilities.
- **Gate:** no automatic global grammar changes from one noisy transcript; no arbitrary generated code is executed.

## M10 — Release evaluation

- Maintain a representative Hindi, Roman Hindi, Hinglish, English, accents, STT-noise, ambiguity, compound-task, web-grounding and failure-recovery benchmark.
- Track intent accuracy, unsafe-guess rate, action verification rate, task completion rate, recovery rate and latency.
- Release only when acceptance thresholds pass on CI and representative Windows hardware.
- **Gate:** CI is green and Windows integration scenarios have evidence; passing unit tests alone is not proof that every app works.

## Development order

M1 -> M2 -> M3 -> M4 -> M5 -> M6. M7 and M8 are integrated with the shared goal/result contracts. M9 remains opt-in and gated. M10 runs throughout the roadmap.

## Explicit limitation

No system can guarantee correct interpretation of every possible sentence or badly corrupted audio. Vyom should use context and safe hypotheses to maximize correct recovery, but ask when meaning is ambiguous, report missing model/network capability honestly, and never claim an unverified desktop action succeeded.
