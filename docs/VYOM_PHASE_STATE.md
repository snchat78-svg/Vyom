# Vyom Phase State — Canonical Cross-Chat Handoff

This is the **authoritative phase register** for continuing work across chats. Read it before starting any phase, then cross-check the branch head, this file, `docs/VYOM_PHASE_CHECKPOINTS.md`, and the latest exact-commit GitHub Actions run. Do not infer completion from a commit message or from code merely existing.

## Repository identity
- Repository: [snchat78-svg/Vyom](https://github.com/snchat78-svg/Vyom)
- Active development branch: `updated`
- Detailed implementation history: [VYOM_PHASE_CHECKPOINTS.md](VYOM_PHASE_CHECKPOINTS.md)
- Roadmap: [VYOM_MIND_DEVELOPMENT_ROADMAP.md](VYOM_MIND_DEVELOPMENT_ROADMAP.md)

## Last verified completed phase — M7.4
- **M7.4 — Pin validated DNS results to the actual outbound socket**
- Exact tested tree: `f417bebeecd902bbfe1111bbad623eaaaeceb4a0`
- Exact-SHA CI: [run 39746025751](https://github.com/snchat78-svg/Vyom/actions/runs/39746025751) — **success**.
- CI result: **364 tests passed, 28 subtests passed**; syntax checks, critical-module imports, voice imports, clean build, Windows EXE build/verification, and `Vyom_EXE` artifact upload all passed.
- Security behavior: for each actual connection, the transport resolves the destination, validates every answer as globally routable, then connects directly to the validated numeric sockaddr from that same result. HTTPS keeps the original hostname for SNI/certificate hostname verification and HTTP Host authority. Redirects are rechecked, and ambient environment proxies are disabled on this fetch path. Malformed/empty DNS results and mixed public/non-public answers fail closed.
- Scope/limitation: the new regression tests use deterministic mocked resolvers/sockets/TLS contexts; CI does not prove every live external network, DNS infrastructure, proxy environment, or real-world TLS scenario. Do not claim M7 as a whole is complete.

## Next phase — READY, NOT STARTED
- **M7.5 — Configurable and bounded retrieval providers**
- Planned target: `ai_core/web_knowledge.py` plus focused tests.
- Requirements:
  1. Define a small provider contract for search/retrieval sources without requiring a remote AI model.
  2. Keep safe public-URL validation, DNS-pinned transport, response byte limits, timeouts, total lookup deadline, source attribution, and unknown-on-failure behavior for every provider path.
  3. Permit deterministic provider injection for tests/offline use; preserve current default retrieval behavior and the backward-compatible singular `source` result field.
  4. Bound provider count, returned results, excerpt length and per-provider work; malformed provider output must be ignored or reported as unavailable rather than trusted.
  5. Test provider ordering/failure, duplicate-host handling, unsafe URLs, output limits, and fallback to `answer_status=unknown` when no usable source remains.
- Completion gate: focused tests and the complete GitHub Actions workflow pass for the exact commit containing code, tests, and phase-record changes.

## Remaining M7 work after M7.5
1. **M7.6:** strengthen contradiction detection beyond numeric/date tokens without pretending lexical overlap proves truth.
2. **M7.7:** add source-quality evaluation and explicit tests for stale, low-quality, duplicate, or weakly attributed sources.
3. Re-audit the complete M7 acceptance gate. Only start M8 once these remaining M7 gates are addressed and tested.

## Cross-chat continuation rules
- This file and `docs/VYOM_PHASE_CHECKPOINTS.md` are the durable handoff. Update both whenever phase status changes; keep the roadmap consistent too.
- Before edits, verify the `updated` branch head and latest Actions run. If a phase is marked complete by exact-SHA CI, **never repeat it**; start the next ordered incomplete item.
- Keep a phase in progress until deterministic tests and exact-commit CI pass. If CI fails, fix the same phase; do not advance.
- For every completed phase, record the implementation/test SHA, exact Actions URL/result, test result, limitations, and next phase.
- Never claim local Windows UI/microphone acceptance from GitHub CI; record such platform testing as external validation.
- On a chat change, start here, verify GitHub's actual branch/run state, then resume only the recorded next phase.

## Change log
- 2026-10-22: M7.3 exact-SHA CI passed on `72815257ca2f7deb89a82b86bee17c904536414a`; its preflight-only DNS check had a time-of-check/time-of-use gap.
- 2026-10-22: M7.4 transport-level DNS pinning passed exact-SHA CI on `f417bebeecd902bbfe1111bbad623eaaaeceb4a0` in [run 39746025751](https://github.com/snchat78-svg/Vyom/actions/runs/39746025751). Next phase is M7.5; M7 remains in progress overall.
