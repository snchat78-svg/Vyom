# Vyom Architecture Roadmap — Phases 1–7

Status is evidence-based: a module existing in the repository does not mean the whole phase is production-complete. The current priority is Phases 1–5. Phase 6 and Phase 7 remain gated until core execution is reliable.

## Phase 1 — Core Wiring Freeze

**1.1 Input contract.** Voice and text enter the same executor. Preserve raw transcript, normalized text, recognized language and session/task context.

**1.2 Goal compiler ownership.** Reuse the ReasoningEngine.goal_compiler instance across the autonomous and deep-reasoning routes. Fix routing defects in shared boundaries instead of adding another command parser for individual examples.

**1.3 Result schema.** Standardize success, status, stage, message, error, result, verification and optional observation metadata. Migrate legacy string-return paths incrementally; strings alone must not prove execution success.

**1.4 Capability registry.** UIAutonomousAgent should use the same registry, resolver and validator instances as its ReasoningEngine. Providers advertise generic actions, not per-app user-command lists.

**1.5 Context ownership.** SessionMemory remains the execution-context owner. ConversationManager may keep bounded presentation history, but must not become a second task-state store.

**1.6 Acceptance gate.** Test object identity, result schema stability, legacy compatibility, and that voice/text follow the same goal/action pipeline.

**Assessment:** The principal components exist. Legacy ToolManager string outputs and response normalization still need incremental migration. The application-open path now has a structured foreground-observation adapter.

## Phase 2 — Generic UI Automation

**2.1 Discovery.** Prefer UI Automation Name, AutomationId, ControlType, class and window identity before coordinates.

**2.2 Grounding.** Rank live candidates, preserve confidence and candidate metadata, and request clarification for near-tied controls.

**2.3 Control patterns.** Prefer Invoke, Value, Selection, Toggle, Expand/Collapse and Focus patterns when the element provides them; use click only as a fallback.

**2.4 Semantic handoff.** Targets such as a search box or power button go to UIA grounding, not the app launcher. Application/file names remain runtime data.

**2.5 Legacy fallback.** Keep existing Win32 and coordinate input when UIA cannot act, but label the result dispatch-only until observation proves the effect.

**2.6 Acceptance gate.** Test varying labels, ambiguous candidates, unavailable UIA and generic targets without app-specific command maps.

**Assessment:** Generic UIA discovery/grounding and control patterns exist. Compound arithmetic is compiled against the runtime-supplied target rather than a fixed calculator-alias list. More Windows-desktop integration tests are needed; runtime verification was expanded so low-level input cannot be VERIFIED solely because dispatch returned.

## Phase 3 — Real Verification

**3.1 Before-state.** Record focused control, active window, relevant UI-tree signature and task state before a state-changing action.

**3.2 Execute.** Pass only validated Action Schema through a registered capability.

**3.3 After-state.** Observe again and evaluate action-specific postconditions. Typing checks observed value; clicking/invoking checks a real focus, tree, window or target effect; open/close checks observed window state.

**3.4 Result gate.** Successful input dispatch without an observable postcondition is not VERIFIED. Keep dispatch metadata but return unverified/failure status.

**3.5 Mission gate.** Dependent steps run only after their required verification passes. Failure must trigger a fresh observation before bounded retry or re-plan.

**3.6 Acceptance gate.** Cover pass, failure, missing observer, no UI change and delayed response with deterministic tests.

**Assessment:** UIA and application open/close already have state checks. This update extends before/after checking to generic click, double-click, keypress, hotkey and scroll actions; broad real-app coverage remains future work.

## Phase 4 — World State 2.0

**4.1 Desktop identity.** Current window/app/file, focused and selected controls, and visible UI elements.

**4.2 Execution trace.** Last action/result/verification, mission state and bounded observation history.

**4.3 Environment.** Running processes, clipboard and screen geometry; capture screen pixels only when a task needs them.

**4.4 Freshness and resilience.** Attach timestamps, bound history, make observations read-only, and ensure observer failures never terminate the voice loop.

**4.5 Acceptance gate.** Test available/unavailable UIA and ensure reasoning receives fresh state after failures.

**Assessment:** WorldStateModel already aggregates most requested fields. Freshness, observation latency and end-to-end quality need validation on the target Windows machine.

## Phase 5 — True Autonomous Loop

**5.1 Observe.** Snapshot before the mission and before each step.

**5.2 Think and plan.** Compile the complete user goal, validate the plan, and preserve step dependency order.

**5.3 Act and verify.** Execute one step and mark it completed only after its postcondition passes.

**5.4 Bounded retry.** Retry only within a set budget; never loop indefinitely on a missing capability or unavailable observer.

**5.5 Re-plan.** Refresh world state after retries fail, reason again using the previous result, and apply a validated plan without repeating completed side effects.

**5.6 Audit.** Keep serializable phase/step events to locate failures at discovery, execution, verification or response handoff.

**5.7 Acceptance gate.** A multi-step task must either complete verified dependent steps or return explicit failure/clarification and resume listening.

**Assessment:** Mission runtime, retries, observation hooks and re-planning are present. Consistent generic result contracts and real desktop observations remain the key blockers.

## Phase 6 — Skill/Capability Learning (deferred)

**6.1 Gap detection.** Record why a goal has no safe capability.

**6.2 Skill specification.** Create a declarative specification only; never execute arbitrary generated Python directly.

**6.3 Static validation and tests.** Validate action names, schema, permissions and deterministic tests in an isolated sandbox.

**6.4 Approval and activation.** Require explicit user permission before registering or enabling a newly generated capability.

**6.5 Outcome learning.** Record a skill outcome only after it runs through the normal capability executor and its result is verified.

**Acceptance gate:** Do not enable self-generation/registration until Phases 1–5 pass representative Windows desktop scenarios. The existing SkillBuilder is planning/scaffolding, not a production-safe self-modifying skill system.

## Phase 7 — Production Intelligence (deferred)

**7.1 Durable local memory.** Store only approved preferences and task outcomes in a versioned, user-controlled local store.

**7.2 Learned aliases.** Save user-approved corrections with confidence, provenance and undo/delete support; do not alter global grammar from one uncertain STT transcript.

**7.3 Workflow memory.** Reuse only workflows with prior verified success and matching current UI preconditions.

**7.4 Failure analytics.** Track latency, failure category, capability/provider, verification result and recovery outcome.

**7.5 Permission memory.** Persist least-privilege approvals with scope, expiry, audit trail and revocation.

**7.6 Privacy and migration.** Add export/delete, schema migration, reset and retention limits before enabling durable personal memory.

**Acceptance gate:** Phase 7 begins only after Phases 1–6 are stable. Bounded SessionMemory and ConversationManager history are not long-term personal memory.

## Intelligence boundary and honest guarantees

Local semantic grammar plus extractive website retrieval can execute known generic action forms and answer factual questions when a suitable source is available. It cannot guarantee fluent, open-domain natural conversation for every possible sentence without a capable language model or broader language-processing component. The current design keeps remote chat/reasoning optional; website-based facts remain source-backed and bounded, not hard-coded fact answers. Unavailable sources must produce an honest failure rather than an invented answer.

## Current validation checklist

- [ ] Wake word, command capture and response handoff complete on the target PC.
- [ ] Unrecognized audio retries without cancelling the active session.
- [ ] Known app launch returns verified success only when the launch effect is observed.
- [ ] Unknown app name returns a clear failure/selection and continues listening.
- [ ] Generic UI target is grounded through live UIA properties and ambiguity is handled safely.
- [ ] Typing/click/keypress results are not marked VERIFIED from dispatch alone.
- [ ] A compound goal preserves ordering, dependencies and per-step verification.
- [ ] Factual question uses website retrieval, displays its source and has a bounded timeout.
- [ ] No provider/source yields an honest uncertainty message.
- [ ] Only after these checks pass should Phase 6/7 implementation begin.
