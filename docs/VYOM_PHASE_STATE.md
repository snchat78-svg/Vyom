# Vyom Phase State — Canonical Cross-Chat Handoff

This is the **authoritative phase register** for continuing work across chats. Read it before starting any phase, then cross-check the branch head, this file, `docs/VYOM_PHASE_CHECKPOINTS.md`, and the latest exact-commit GitHub Actions run. Do not infer completion from a commit message or from code merely existing.

## Repository identity
- Repository: [snchat78-svg/Vyom](https://github.com/snchat78-svg/Vyom)
- Active development branch: `updated`
- Detailed implementation history: [VYOM_PHASE_CHECKPOINTS.md](VYOM_PHASE_CHECKPOINTS.md)
- Roadmap: [VYOM_MIND_DEVELOPMENT_ROADMAP.md](VYOM_MIND_DEVELOPMENT_ROADMAP.md)

## Last verified completed phase
- **M7.3 — DNS-aware public destination preflight**
- Verified source commit: `72815257ca2f7deb89a82b86bee17c904536414a`
- Exact commit CI: [run 39741822185](https://github.com/snchat78-svg/Vyom/actions/runs/39741822185) — success. Complete test suite, syntax/import checks, Windows EXE build, EXE verification, and artifact upload passed.
- Acceptance delivered: web-fetch and redirect preflight rejects DNS failure, empty answer sets, and any non-global address in a resolved set.
- Known limitation: this was a preflight check. The stock urllib transport resolves the hostname again at connection time, leaving a DNS time-of-check/time-of-use gap. Do **not** claim full DNS-rebinding protection from M7.3 alone.

## Current phase — IN PROGRESS
- **M7.4 — Pin validated DNS results to the actual outbound socket**
- Implementation target: `ai_core/web_knowledge.py`
- Regression tests: `tests/test_web_knowledge.py`
- Requirements:
  1. Resolve the origin for the actual connection, validate every returned address as globally routable, and fail closed on resolver failure, malformed/empty records, or any non-global answer.
  2. Connect directly to a validated numeric socket address from that exact resolution result; do not perform a second hostname lookup between validation and connect.
  3. For HTTPS, preserve the original hostname for TLS SNI and certificate/hostname verification, while the TCP socket connects to the pinned IP.
  4. Keep the original HTTP Host authority, re-apply the public-DNS policy for every redirect, and disable ambient proxies for this security-sensitive fetch path so a proxy cannot bypass local IP pinning.
  5. Add deterministic tests using a fake resolver/socket/context; no real external network dependency in tests.
- Completion gate: the focused web-knowledge tests and full GitHub Actions workflow must pass for the exact commit that contains the code/tests/docs. Any remaining limitation must be documented honestly.

## Ordered remaining M7 work
1. **M7.4 (current):** transport-level DNS pinning / close the preflight-to-connect gap.
2. **M7.5:** make source retrieval providers configurable and bounded, with safe defaults and offline/test injection.
3. **M7.6:** strengthen contradiction detection beyond numeric/date tokens without pretending lexical overlap proves truth.
4. **M7.7:** add source-quality evaluation and explicit tests for stale, low-quality, duplicate, or weakly attributed sources.
5. Re-audit the entire M7 acceptance gate before marking M7 complete. Only proceed to M8 after the remaining M7 gates and documented tests are addressed.

## Cross-chat continuation rules
- This file and `docs/VYOM_PHASE_CHECKPOINTS.md` are the durable handoff. Update both when a phase changes state.
- Before any edits, verify branch `updated` head and latest actions run. If the current phase is marked complete by exact-SHA CI, **never repeat it**; start the next ordered incomplete item.
- Keep a phase **in progress** until deterministic tests and exact-commit CI pass. If CI fails, fix the same phase; do not advance.
- After each phase, append the implementation commit SHA, exact Actions run URL/result, test result, limitations, and next phase.
- Never claim local Windows UI/microphone acceptance from GitHub CI; record that as external validation where relevant.
- Current most recent documentation update is not itself evidence that a new code phase has passed CI.

## Change log
- 2026-10-22: M7.3 exact-SHA CI confirmed successful on `72815257ca2f7deb89a82b86bee17c904536414a`; M7.4 selected as the next incomplete M7 security increment.
