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

## Phase matrix

| Phase/checkpoint | Existing implementation and evidence | Status before M0.3 | Remaining acceptance |
|---|---|---|---|
| M0 baseline / exit gate | Shared ConversationManager, canonical result schema, bounded history, trace summaries, bounded plan topology, and voice/text executor parity | Implemented + exact-commit CI tested (run 39401980752) | Real Windows/microphone and cross-app acceptance |
| M0.1 input trace | `voice/voice_controller.py`, `ai_core/conversation_manager.py`, `tests/test_conversation_manager.py`; raw STT text, normalized input, confidence, corrections, result stage and verification status | Implemented + CI tested | Real Windows microphone/voice round-trip |
| M0.2 pipeline trace | `command_engine/executor.py`, `ai_core/conversation_manager.py`; trace ID, intent/route, compact goal-compilation/mission/context summaries and privacy tests | Implemented + CI tested | Observation events linked to the same trace |
| M0.3 observation correlation | Same-turn timestamped observations linked to trace ID; payload-free event summaries and no-observation state; validated by run 39399731304 | Implemented + CI tested | Real Windows observation behavior remains part of integration validation |
| M0.4 shared frontend | `ai_core/main.py`, `voice/voice_controller.py` and `tests/test_m0_4_shared_frontend.py`; same manager handles typed and spoken turns | Implemented + CI tested (run 39400224264) | Real Windows interactive acceptance remains pending |
| M1 noisy speech | Payload-safe command normalization, runtime candidate margin, exact AppsFolder unique-match gate, target typo/ambiguity/clarification coverage | Automated gate passed exact-SHA CI run 39405455918 | Real microphone/accent and interactive Windows/cross-app validation |
| M2 meaning/intent | Meaning frame, generic targets, confidence threshold, clarification-before-dispatch, stateless normalization and terminal plan-precedence guard | Automated acceptance passed exact-SHA CI: runs 39405929075, 39415383368, 39416145129, 39416613583 and 39417115798 | Representative paraphrase/noisy-voice benchmark and real desktop/microphone validation; future persistent learning remains opt-in M9 work |
| M3 complex planning | Dependency graph/re-plan guards plus generic risk metadata and pre-dispatch confirmation hold | Risk-policy/schema/confirmation suite passed exact-SHA CI run 39418664644; build and EXE verification passed | Broader irreversible-effect coverage and real multi-step Windows acceptance |
| M4 world state | M4.1–M4.6 documented in roadmap; `ai_core/world_state.py`, `tests/test_phase4_world_state.py` | Implemented automated guards; platform validation pending | Fresh active-window/focus behavior on user's Windows PC |
| M5 action grounding | M5.1–M5.5 documented in roadmap; UI grounder/verifier tests | Implemented automated guards; platform validation pending | Real controls, layouts and foreground changes |
| M6 execution/recovery | M6.1–M6.6 documented in roadmap; mission runtime, recovery tests and durable journal | Implemented automated guards; platform validation pending | Real delayed effects, restart, and side-effect validation |
| M7 web/source answers | Web knowledge and provider groundwork exist; roadmap acceptance gate not proven complete | Partial/planned | Source-backed fact retrieval and citation quality tests |
| M8 general reasoning | Provider/goal-routing groundwork exists; broad benchmark not complete | Partial/planned | Provider outage behavior and sourced/unknown answer evaluation |
| M9 opt-in learning | Skill/memory modules exist; safe user-approved end-to-end gate not established here | Partial/planned | Consent, provenance, expiry/export/deletion acceptance |
| M10 release evaluation | CI suite exists; representative full benchmark and real-device evidence are incomplete | Ongoing/incomplete | Metrics thresholds and Windows integration evidence |

## Current phase hand-off

- M2 target-preservation patch `d40edb47ebc0be055c7a3b337661e70dcf80f11a` passed exact-SHA [CI run 39405929075](https://github.com/snchat78-svg/Vyom/actions/runs/39405929075); explicit generic UI targets such as `click Save` remain in the meaning frame.
- M2 confidence/hypothesis increment `d0dd7910c32169f1884759254e47b969c38429c8` passed exact-SHA [CI run 39415383368](https://github.com/snchat78-svg/Vyom/actions/runs/39415383368), including complete tests and Windows EXE build/verification/upload. Low/invalid-confidence action hypotheses stay unresolved.
- M2 local-semantic dispatch gate `74c6ec0c5f0baafd40272bf32342ee00d0dbc268` passed exact-SHA [CI run 39416145129](https://github.com/snchat78-svg/Vyom/actions/runs/39416145129): low-confidence executable plans and tied target candidates return terminal clarification with an empty plan.
- Stateless-normalization regression `7a92d936ab84322610bb7f6ab15725ea90fc36ed` passed exact-SHA [CI run 39416613583](https://github.com/snchat78-svg/Vyom/actions/runs/39416613583); unknown targets do not become learned aliases across turns. Persistent user-approved learning remains opt-in M9 work.
- Terminal-route precedence and no-plan guard `d1001544bd50dd308fe7293132aa4c72be2b0e2e` passed exact-SHA [CI run 39417115798](https://github.com/snchat78-svg/Vyom/actions/runs/39417115798), including complete tests and Windows EXE build/verification/upload. Terminal semantic clarification now outranks any stale model/contextual plan and yields no execution steps. M2 automated confidence, target-preservation, correction-state and route-precedence gates are green; noisy-voice benchmark and actual Windows desktop/microphone validation remain external. M3 audit follows without claiming M2 platform validation.
- M3 first increment `7e7cdd4aa604b6e71b3fdc0532f8a336ce5781d2` passed exact-SHA [CI run 39418664644](https://github.com/snchat78-svg/Vyom/actions/runs/39418664644), including 330+ passing tests and Windows EXE build/verification/upload. High-impact plans are held before MissionRuntime starts; unrelated commands cannot bypass pending confirmation; explicit confirm reuses the stored plan and cancel discards it. Risk heuristics remain conservative and app-specific risk coverage plus real desktop acceptance remain incomplete.
