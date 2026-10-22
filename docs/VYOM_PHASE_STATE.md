# Vyom Phase State — Canonical Cross-Chat Handoff

This is the **authoritative phase register** for continuing work across chats. Read it before starting a phase, then cross-check the branch head, this file, `docs/VYOM_PHASE_CHECKPOINTS.md`, and the latest exact-commit GitHub Actions run. Do not infer completion from a commit message or from code merely existing.

## Repository identity
- Repository: [snchat78-svg/Vyom](https://github.com/snchat78-svg/Vyom)
- Active development branch: `updated`
- Detailed implementation history: [VYOM_PHASE_CHECKPOINTS.md](VYOM_PHASE_CHECKPOINTS.md)
- Roadmap: [VYOM_MIND_DEVELOPMENT_ROADMAP.md](VYOM_MIND_DEVELOPMENT_ROADMAP.md)

## Last verified completed phase — M7.4
- **M7.4 — Pin validated DNS results to the actual outbound socket**
- Exact tested tree: `f417bebeecd902bbfe1111bbad623eaaaeceb4a0`
- Exact-SHA CI: [run 39746025751](https://github.com/snchat78-svg/Vyom/actions/runs/39746025751) — **success**.
- CI result: 364 tests passed, 28 subtests passed; syntax/import checks, clean build, Windows EXE verification and artifact upload passed.
- Limitation: mocked socket/resolver tests do not establish every live network/TLS environment. M7 as a whole remains incomplete.

## Current phase — IN PROGRESS
- **M7.5 — Configurable and bounded retrieval providers**
- Code: `ai_core/web_knowledge.py`; tests: `tests/test_web_knowledge.py`.
- Initial implementation/test commit `d3bc1217228b841cd161787a9b08f1e6db0b4216` passed [exact-SHA CI run 39753077159](https://github.com/snchat78-svg/Vyom/actions/runs/39753077159): 372 tests and 28 subtests passed, Windows EXE verification and artifact upload passed. A direct provider-count regression, implementation docstrings, and the synchronized phase records were then added; verify the newest exact-SHA run before marking M7.5 complete.
- Contract: `RetrievalProvider(name, retrieve, max_results=3)`; callback signature is `retrieve(client, query_variants, preferred_language)`. A callback returns one result mapping or a finite list/tuple of mappings. Valid output needs `success=True`, answer, evidence text, and a public HTTP(S) source URL.
- Safe fetch helper: `client.fetch_text(url)`. Provider implementations should use this rather than opening sockets directly; it uses the shared public URL check, DNS-aware pinned transport, byte cap, timeouts, and total lookup deadline.
- Bounds: at most 4 configured providers considered, at most 3 results accepted per provider, at most 6 results collected in one lookup, at most 6 fetches per provider / 12 aggregate fetches, excerpt at most 1,200 characters, source URL at most 2,048 characters, title at most 240, site at most 160, answer at most 2,400. Providers are invoked once per lookup; provider exceptions and malformed outputs are isolated, and duplicate normalized hosts are deduplicated.
- Compatibility/safety: when `providers=None`, the default Wikipedia and DuckDuckGo paths remain enabled. An explicitly empty provider collection disables retrieval and yields `answer_status=unknown`; citations with unsafe URLs are rejected. The legacy singular `source` field remains available alongside `sources`.
- Acceptance gate: focused provider tests and the complete exact-commit Actions workflow must pass, including Windows EXE build, verification and artifact upload. Do not mark complete until the final code/test/docs commit has green CI.

## Next phases after M7.5
1. **M7.6:** strengthen contradiction detection beyond numeric/date tokens without pretending lexical overlap proves truth.
2. **M7.7:** evaluate source quality and test stale, low-quality, duplicate, or weakly attributed sources.
3. Re-audit M7 before starting M8. M7 must not be marked complete until all remaining gates are tested.

## Cross-chat continuation rules
- This file and `docs/VYOM_PHASE_CHECKPOINTS.md` are the durable handoff. Update both whenever phase status changes; keep the roadmap consistent too.
- Before edits, verify the `updated` branch head and latest Actions run. If a phase is marked complete by exact-SHA CI, **never repeat it**; start the next ordered incomplete item.
- Keep a phase in progress until deterministic tests and exact-commit CI pass. If CI fails, fix the same phase; do not advance.
- For each completed phase, record the implementation/test SHA, exact Actions URL/result, test result, limitations, and next phase.
- Do not claim local Windows UI/microphone acceptance from GitHub CI.
- On a chat change, start here, verify GitHub's actual branch/run state, then resume only the recorded next phase.

## Change log
- 2026-10-22: M7.3 DNS preflight passed exact-SHA CI on `72815257ca2f7deb89a82b86bee17c904536414a`; M7.4's connection-level DNS pinning passed on `f417bebeecd902bbfe1111bbad623eaaaeceb4a0` in [run 39746025751](https://github.com/snchat78-svg/Vyom/actions/runs/39746025751).
- 2026-10-22: M7.5 provider implementation and its first test matrix passed on `d3bc1217228b841cd161787a9b08f1e6db0b4216` in [run 39753077159](https://github.com/snchat78-svg/Vyom/actions/runs/39753077159). M7.5 remains in progress pending latest full acceptance run.
