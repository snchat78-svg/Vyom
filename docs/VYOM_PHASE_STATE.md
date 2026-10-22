# Vyom Phase State — Canonical Cross-Chat Handoff

This is the **authoritative phase register** for continuing work across chats. Read it before starting a phase, then cross-check the branch head, this file, `docs/VYOM_PHASE_CHECKPOINTS.md`, and the latest exact-commit GitHub Actions run. Do not infer completion from a commit message or from code merely existing.

## Repository identity
- Repository: [snchat78-svg/Vyom](https://github.com/snchat78-svg/Vyom)
- Active development branch: `updated`
- Detailed implementation history: [VYOM_PHASE_CHECKPOINTS.md](VYOM_PHASE_CHECKPOINTS.md)
- Roadmap: [VYOM_MIND_DEVELOPMENT_ROADMAP.md](VYOM_MIND_DEVELOPMENT_ROADMAP.md)

## Last verified completed phase — M7.5
- **M7.5 — Configurable and bounded retrieval providers**
- Exact tested tree: `90ae4ead63c586b8da98191d5266254736c5269d`
- Exact-SHA CI: [run 39753595589](https://github.com/snchat78-svg/Vyom/actions/runs/39753595589) — **success**.
- CI result: **373 tests passed, 28 subtests passed**; tracked-file/syntax/import checks, clean build, Windows EXE build/verification and `Vyom_EXE` artifact upload passed.
- Provider API: `RetrievalProvider(name, retrieve, max_results=3)`, callback signature `retrieve(client, query_variants, preferred_language)`.
- Bounds: at most 4 configured providers, 3 accepted results/provider, 6 results/lookup, 6 fetches/provider and 12 total, 1,200-character excerpt, 2,048-character source URL, 240-character title, 160-character site and 2,400-character answer.
- Safety: provider outputs require a successful mapping, evidence, answer and a public HTTP(S) citation. Exceptions and malformed output do not stop later providers. Custom HTTP retrieval should use `client.fetch_text()` for the shared URL/DNS-pinned transport, timeout, body-size and lookup-deadline checks. Empty configured provider list, invalid outputs or no usable sources return `answer_status=unknown`; legacy `source` remains alongside `sources`.
- Limitation: provider callbacks are trusted local Python integrations, not a sandbox for arbitrary code. Network bounds apply when they use `client.fetch_text()`; real external-network behavior still needs environment-level validation. M7 overall is not complete.

## Next phase — READY, NOT STARTED
- **M7.6 — Broader semantic contradiction detection**
- Improve conflict detection beyond numeric/date-like values while avoiding claims that lexical overlap proves truth.
- Keep uncertain contradictions unresolved rather than guessing. Add deterministic tests for non-numeric opposing claims, paraphrased claims, unrelated sentences and compatible claims that use different wording.
- Preserve source attribution and the existing `single_source`, `textually_aligned`, `potential_numeric_conflict`, and `divergent_unresolved` behaviors unless tests justify a documented schema change.

## Remaining M7 work after M7.6
1. **M7.7:** source-quality evaluation and tests for stale, low-quality, duplicate, weakly attributed or low-evidence sources.
2. Re-audit the full M7 gate. Only start M8 after M7.6, M7.7 and the overall acceptance audit pass.

## Cross-chat continuation rules
- This file and `docs/VYOM_PHASE_CHECKPOINTS.md` are the durable handoff. Update both whenever phase status changes; keep the roadmap consistent too.
- Before edits, verify the `updated` branch head and latest Actions run. If a phase is marked complete by exact-SHA CI, **never repeat it**; start the next ordered incomplete item.
- Keep a phase in progress until deterministic tests and exact-commit CI pass. If CI fails, fix the same phase; do not advance.
- For each completed phase, record the implementation/test SHA, exact Actions URL/result, test result, limitations, and next phase.
- Do not claim local Windows UI/microphone acceptance from GitHub CI.
- On a chat change, start here, verify GitHub's actual branch/run state, then resume only the recorded next phase.

## Change log
- 2026-10-22: M7.3 DNS preflight passed exact-SHA CI on `72815257ca2f7deb89a82b86bee17c904536414a`.
- 2026-10-22: M7.4 DNS-pinned transport passed exact-SHA CI on `f417bebeecd902bbfe1111bbad623eaaaeceb4a0` in [run 39746025751](https://github.com/snchat78-svg/Vyom/actions/runs/39746025751).
- 2026-10-22: M7.5 configurable/bounded retrieval providers passed exact-SHA CI on `90ae4ead63c586b8da98191d5266254736c5269d` in [run 39753595589](https://github.com/snchat78-svg/Vyom/actions/runs/39753595589): 373 tests and 28 subtests, Windows EXE verification/upload. Next phase: M7.6; M7 overall remains partial.
