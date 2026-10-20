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
- M1 payload-preservation repair is the current patch in CI: `voice/command_normalizer.py` now avoids changing target/payload words after recognized command markers; added tests cover `type khol`, `open khol`, and a compound command whose next segment still normalizes. Do not mark M1 complete from this patch alone; ambiguity/margin acceptance and real audio remain outstanding.

## Phase matrix

| Phase/checkpoint | Existing implementation and evidence | Status before M0.3 | Remaining acceptance |
|---|---|---|---|
| M0 baseline / exit gate | Shared ConversationManager, canonical result schema, bounded history, trace summaries, bounded plan topology, and voice/text executor parity | Implemented + exact-commit CI tested (run 39401980752) | Real Windows/microphone and cross-app acceptance |
| M0.1 input trace | `voice/voice_controller.py`, `ai_core/conversation_manager.py`, `tests/test_conversation_manager.py`; raw STT text, normalized input, confidence, corrections, result stage and verification status | Implemented + CI tested | Real Windows microphone/voice round-trip |
| M0.2 pipeline trace | `command_engine/executor.py`, `ai_core/conversation_manager.py`; trace ID, intent/route, compact goal-compilation/mission/context summaries and privacy tests | Implemented + CI tested | Observation events linked to the same trace |
| M0.3 observation correlation | Same-turn timestamped observations linked to trace ID; payload-free event summaries and no-observation state; validated by run 39399731304 | Implemented + CI tested | Real Windows observation behavior remains part of integration validation |
| M0.4 shared frontend | `ai_core/main.py`, `voice/voice_controller.py` and `tests/test_m0_4_shared_frontend.py`; same manager handles typed and spoken turns | Implemented + CI tested (run 39400224264) | Real Windows interactive acceptance remains pending |
| M1 noisy speech | `voice/command_normalizer.py`; current audit confines action correction to command boundaries and protects target/payload suffixes | First payload-preservation fix added; exact-commit CI pending | Tied target-candidate clarification, complete typo/ambiguity regression audit, and real microphone/accent benchmark |
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

M0.1–M0.4 and the automated M0 exit gate are complete; source commit `b92d277ebdb5a9bb49469612e4388b1979ff044c` passed exact-SHA CI run 39401980752. Do not repeat M0. The M1 payload-preservation patch in this checkpoint fixes a demonstrated risk: Hindi action aliases no longer rewrite words inside explicit target/payload suffixes, while command markers after connectors remain normalizable. Its CI result is pending. If green, the next M1 task is to audit runtime target-candidate confidence/margin and tied-match clarification without recreating the existing MeaningIntentEngine/resolver logic. Real microphone/accent and desktop interaction remain external platform checks.
