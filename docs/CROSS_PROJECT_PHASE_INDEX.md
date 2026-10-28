# Cross-Project Phase Continuity Index

This is the central navigation page for the repositories visible through the current GitHub connection. Each project still owns its own authoritative phase register. Before starting work in a project, open that repository's state/registry, then verify its live branch head and latest applicable CI.

## Projects and current handoff

| Repository | Canonical state | Last verified / current condition | Next recorded work |
|---|---|---|---|
| [Vyom](https://github.com/snchat78-svg/Vyom) | [VYOM_PHASE_STATE.md](VYOM_PHASE_STATE.md) | Latest exact-SHA CI [40631719205](https://github.com/snchat78-svg/Vyom/actions/runs/40631719205) passed 1144c8de227a2a5d344ddf3aa17a7f5792305b3a: 473 tests + 30 subtests, M10.2/M10.3 22/22 thresholds, EXE verification and artifacts. | **M10.4 remains in progress and blocked on actual target-device evidence.** Current package artifact 12792081432; observed log review and regression fixes documented. M10.5 remains blocked. |
| [AI-COMP](https://github.com/snchat78-svg/AI-COMP) | [PHASE_REGISTRY.md](https://github.com/snchat78-svg/AI-COMP/blob/main/docs/PHASE_REGISTRY.md) | Main head `40ff0dfbaa4c3255045bcdb35012121c840e40e7`; [run 39758390037](https://github.com/snchat78-svg/AI-COMP/actions/runs/39758390037) passed. Phase 6.55 is `MERGED_CODE_DATA_PENDING`; live reviewer/migration/data gates remain. Phase 6.58 is blocked on approved official-source connectivity. | Phase 6.56 is the next PLANNED implementation item in the existing registry; read the registry and master roadmap before selecting work. |
| [vyom-from-AI-studio](https://github.com/snchat78-svg/vyom-from-AI-studio) | [PHASE_STATE.md](https://github.com/snchat78-svg/vyom-from-AI-studio/blob/main/docs/PHASE_STATE.md) | The latest observed code/build CI failed on `2829a4c9fe3da130e0b5d926a4f1c987789c613b`; [run 34122666402](https://github.com/snchat78-svg/vyom-from-AI-studio/actions/runs/34122666402). Later commits added continuity documentation only and did not fix the application build. | STUDIO-0 — Baseline inventory and build-health audit. |
| [nchat](https://github.com/snchat78-svg/nchat) | [PHASE_STATE.md](https://github.com/snchat78-svg/nchat/blob/main/docs/PHASE_STATE.md) | Latest observed workflow success is [run 30822392713](https://github.com/snchat78-svg/nchat/actions/runs/30822392713) on application-code head `696c458cbbbeeefecb517792074f0091b0d6ff1a`. This was associated with reCAPTCHA diagnostics, not full production/device acceptance. Subsequent commits were documentation-only. | NCHAT-0 — Baseline inventory and acceptance audit. |

## Shared rule
All four repositories contain `docs/PHASE_CONTINUITY_STANDARD.md` or an equivalent linked policy. At every new phase, read the project's state first; verify branch/head and latest CI; check for existing implementation; choose only the next incomplete phase; and update the state/checkpoint/roadmap after exact-SHA validation. Never mark a phase complete based only on a commit, file creation, older green run or diagnostic-only workflow.

## Memory and repository scope
This index is durable GitHub documentation, not an account-level ChatGPT memory write. It covers the four repositories listed by the connected GitHub repository listing when this index was created. Any other repository should adopt its own standard and state file before work continues there.
