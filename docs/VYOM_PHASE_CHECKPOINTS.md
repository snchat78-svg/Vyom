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
- Last verified implementation checkpoint: `3feb985aad0fe5c6c31c1be6189b7363f6a0d616`
- CI evidence for that checkpoint: [run 39399731304](https://github.com/snchat78-svg/Vyom/actions/runs/39399731304), successful; 299 passed, 12 subtests passed; Windows `Vyom.exe` built, verified and uploaded.
- M0.3 is implemented + CI tested at that checkpoint. It reuses the existing M4 WorldState history and M5/M6 verification output; do not rebuild observers or verifiers.
- New gap found by audit: `ai_core/main.py` sent typed input straight to `execute`, while voice used `ConversationManager`; text therefore skipped the bounded conversation turn/trace path. M0.4 routes both through the same manager instance.
- M0.4 is the current candidate in this checkpoint; read the newest workflow for the exact current branch SHA before deciding it is accepted. If green, do not reimplement M0.4; continue to the M0 exit-gate audit. If failed, fix only the failing regression.

## Phase matrix

| Phase/checkpoint | Existing implementation and evidence | Status before M0.3 | Remaining acceptance |
|---|---|---|---|
| M0 baseline | Shared ConversationManager, canonical result schema, bounded history, no success-by-response-text inference | Partial | Whole shared pipeline trace and regression evidence |
| M0.1 input trace | `voice/voice_controller.py`, `ai_core/conversation_manager.py`, `tests/test_conversation_manager.py`; raw STT text, normalized input, confidence, corrections, result stage and verification status | Implemented + CI tested | Real Windows microphone/voice round-trip |
| M0.2 pipeline trace | `command_engine/executor.py`, `ai_core/conversation_manager.py`; trace ID, intent/route, compact goal-compilation/mission/context summaries and privacy tests | Implemented + CI tested | Observation events linked to the same trace |
| M0.3 observation correlation | Same-turn timestamped observations linked to trace ID; payload-free event summaries and no-observation state; validated by run 39399731304 | Implemented + CI tested | Real Windows observation behavior remains part of integration validation |
| M0.4 shared frontend | `ai_core/main.py` and `voice/voice_controller.py`; the same ConversationManager handles typed and spoken turns | Candidate implementation; CI pending for current commit | One shared manager/trace path; no direct text-to-executor bypass; regression test |
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

M0.3 is complete at commit `3feb985` with green CI. M0.4 is the current candidate: typed input now shares the exact ConversationManager instance used by voice, closing a gap discovered during source audit. Check the latest workflow for the current branch head. If green, move to the M0 exit-gate audit (voice/text executor parity and verified-success contract) without reimplementing M0.1–M0.4. If red, fix only the failing tests/code.
