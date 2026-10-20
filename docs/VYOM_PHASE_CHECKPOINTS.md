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
- Last fully green commit before M0.3 work: `f902dd68a6cf4fb84dc6328bcd8fd2c166b95ffa`
- Last fully green workflow: [run 39398606744](https://github.com/snchat78-svg/Vyom/actions/runs/39398606744)
- Test evidence from that run: 297 passed, 12 subtests passed.
- Windows build evidence from that run: `Vyom.exe` built, verified and artifact uploaded.
- M0.3 scope: **correlate already-recorded same-turn observations to the M0 trace**. Do not rebuild WorldState, ObservationVerifier or UI postcondition verification; those already exist under M4/M5/M6.

## Phase matrix

| Phase/checkpoint | Existing implementation and evidence | Status before M0.3 | Remaining acceptance |
|---|---|---|---|
| M0 baseline | Shared ConversationManager, canonical result schema, bounded history, no success-by-response-text inference | Partial | Whole shared pipeline trace and regression evidence |
| M0.1 input trace | `voice/voice_controller.py`, `ai_core/conversation_manager.py`, `tests/test_conversation_manager.py`; raw STT text, normalized input, confidence, corrections, result stage and verification status | Implemented + CI tested | Real Windows microphone/voice round-trip |
| M0.2 pipeline trace | `command_engine/executor.py`, `ai_core/conversation_manager.py`; trace ID, intent/route, compact goal-compilation/mission/context summaries and privacy tests | Implemented + CI tested | Observation events linked to the same trace |
| M0.3 observation correlation | Existing `WorldStateModel.record_observation`, `AutonomousAgent._observe_cycle`, and verifier outputs are in repository; no same-turn event summary was attached to the M0 trace before this checkpoint | In progress | Same-turn timestamp filter, explicit verification evidence, redaction, no-observation marker and tests |
| M1 noisy speech | `voice/command_normalizer.py` and its typo/ambiguity tests | Foundation + CI tests | Representative real microphone/accent benchmark |
| M2 meaning/intent | `command_engine/intent.py`, `ai_core/meaning_intent_engine.py` and ambiguity/context tests | Foundation + CI tests | Paraphrase/noisy voice validation, ask instead of guessing |
| M3 complex planning | `ai_core/goal_compiler.py`, `ai_core/mission_planner.py`, dependency-validation tests | Foundation + CI tests | Real multi-step Windows acceptance |
| M4 world state | M4.1–M4.6 documented in roadmap; `ai_core/world_state.py`, `tests/test_phase4_world_state.py` | Implemented automated guards; platform validation pending | Fresh active-window/focus behavior on user's Windows PC |
| M5 action grounding | M5.1–M5.5 documented in roadmap; UI grounder/verifier tests | Implemented automated guards; platform validation pending | Real controls, layouts and foreground changes |
| M6 execution/recovery | M6.1–M6.6 documented in roadmap; mission runtime, recovery tests and durable journal | Implemented automated guards; platform validation pending | Real delayed effects, restart, and side-effect validation |
| M7 web/source answers | Web knowledge and provider groundwork exist; roadmap acceptance gate not proven complete | Partial/planned | Source-backed fact retrieval and citation quality tests |
| M8 general reasoning | Provider/goal-routing groundwork exists; broad benchmark not complete | Partial/planned | Provider outage behavior and sourced/unknown answer evaluation |
| M9 opt-in learning | Skill/memory modules exist; safe user-approved end-to-end gate not established here | Partial/planned | Consent, provenance, expiry/export/deletion acceptance |
| M10 release evaluation | CI suite exists; representative full benchmark and real-device evidence are incomplete | Ongoing/incomplete | Metrics thresholds and Windows integration evidence |

## Current phase hand-off

M0.3 is the only active implementation checkpoint. Its deliverable is a privacy-minimized observation-evidence object under each conversation trace. After its CI is green, audit the trace end-to-end once before selecting any new phase. Do not move to M0.4 or M1 while M0.3 has a failing test or lacks same-commit green CI.
