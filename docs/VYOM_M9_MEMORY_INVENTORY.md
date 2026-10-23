# Vyom M9.1 — Memory and persistence baseline inventory

**Phase status:** M9.1 completed on exact-SHA CI; this is still a design/inventory artifact, not activation of long-term personal memory. Acceptance: [run 39900778509](https://github.com/snchat78-svg/Vyom/actions/runs/39900778509) — 399 tests + 30 subtests and Windows EXE verification/upload.
**Branch:** `updated`
**Owner of phase truth:** `docs/VYOM_PHASE_STATE.md`
**Proposed schema:** `docs/schemas/vyom_user_memory.v1.schema.json`

## Findings summary

1. `memory/session_memory.py` implements process-local working context. It stores the current goal/instruction, app/file/target, last action/result, confirmation/selection state and bounded conversation/task histories. Each history is trimmed to 100 entries. It has no path or persistence API. `reset()` clears histories and task state; `end_session()` marks the state closed but does not itself erase all retained values from the live object.
2. `ai_core/conversation_manager.py` retains a bounded in-process turn history (default maximum 20). A turn can contain input text, response text and trace metadata; voice traces can include raw transcripts. This is useful runtime/debug context, not a consented long-term memory record.
3. `memory/selection_manager.py` retains search/selection results only in the current object. Its class does not provide persistent storage or its own list-size cap; any future memory feature must not reuse it as a durable store.
4. `ai_core/skill_registry.py` is the existing persistent JSON store, defaulting to `skills/registry.json`. It writes skill/capability specifications including `goal`, `description`, `requirements` and `plan`. New entries are `planned`, `enabled=False`, `validated=False`, `approved=False`, `executable=False`; enabling requires both validation and approval. **Important distinction:** approval currently gates enablement, not the initial persistence of the full goal/plan. Treat this as a capability registry, not the new personal-memory store, and review retention/visibility in later M9 phases.
5. `ai_core/mission_runtime.py` optionally persists a separate fail-closed recovery marker. The Windows default is under `%LOCALAPPDATA%\\Vyom\\recovery_state.json`; non-Windows uses the XDG state directory. The schema contains a version, active flag, bounded category, SHA-256 fingerprint and creation time; the implementation intentionally excludes goal text, target, action name/arguments, typed text, clipboard contents and the runnable plan. Existing `tests/test_m6_5_recovery_journal.py` covers payload exclusion, restart lock and failure-closed cases.
6. `ai_core/logger.py` prints to stdout rather than writing its own log file. Some callers may include a bounded question or error text in messages, so external console/service capture remains an environment-level retention boundary.
7. `ai_core/model_gateway.py` reads user-local configuration from env files; it does not implement a personal preference/correction store.

## Source-to-requirement map

| Existing source | Data and current lifecycle | M9 requirement / disposition |
|---|---|---|
| `SessionMemory` | Transient goal, instruction, app/file/target, actions/results and up to 100 history items per history; no disk persistence method | Keep transient execution state distinct from durable user memory. Add explicit end/clear behavior and privacy tests before integrating any persistent learner. |
| `ConversationManager` | In-process recent turns; text/trace can include transcript content; default max history 20 | Never serialize the whole turn/trace into long-term memory. Only approved, minimal references may be used as provenance. |
| `SelectionManager` | Current result list in an object; not durable | Do not use as long-term memory. Bound any values projected into a future memory record. |
| `SkillRegistry` | Atomic JSON write to `skills/registry.json`; stores specification fields including user-supplied goal/plan; no schema version/expiry in each record | Keep it separate from preference memory. Make runtime registry files non-committable; later review consent, visible scope, expiry and deletion expectations for persisted proposals. |
| `MissionRuntime` recovery journal | Minimal fail-closed marker, not a remembered preference/workflow | Reuse existing recovery journal; do not duplicate or expand it into an execution-memory database. |
| `ModelGateway` env loading | User-local endpoint/model/API-key configuration | Keep credentials outside memory records, schema fixtures, logs and source control. |

## Proposed record contract (schema v1)

The JSON Schema file is a **design contract only** at M9.1; runtime code does not read or write it yet. Later phases must add a validated storage adapter and explicit consent before it is activated.

- `schema_version=1`; unique `memory_id`; type is one of `correction`, `preference`, `verified_workflow`.
- A correction stores bounded surface/preferred forms and optional language/context hints; a preference stores a bounded key/value and scope hint; a verified-workflow entry stores a stable workflow reference and summary, not a runnable action plan or payload.
- Scope is explicit (`global`, `application`, or `workflow`); each record carries creation/update/expiry, lifecycle status, confidence in the interpretation (0–1), source provenance and an approval envelope.
- Approval must be explicit user consent with a consent version and non-content decision reference. A provider/model confidence score is not user consent.
- Source references must be opaque identifiers, not raw utterances or transcripts. The record must not contain credentials, API keys, clipboard payloads, raw conversation history, unrestricted file contents, or arbitrary webpage text.
- Memory may inform a suggestion; it cannot override ambiguity checks, world-state freshness, action validation, explicit confirmations, postcondition verification or execution permissions.

## Data lifecycle and privacy matrix

| Stage | Required behavior | Failure/default |
|---|---|---|
| Candidate creation | In-memory candidate only; identify whether it is a correction, preference or previously verified workflow | Do not persist by default |
| Consent | User explicitly opts in and approves the specific record/scope | Missing, stale or revoked consent => reject write |
| Validation | Validate schema, types, bounds, provenance, confidence and expiry; reject secret/raw-payload-like fields | Invalid record => fail closed, no partial write |
| Storage | Versioned atomic file/database writes via a future dedicated adapter; records stay user-local and outside Git | Storage error => no silent in-memory/persistent inconsistency |
| Use | Filter by active lifecycle, scope and expiry; use only as a hint | Never authorize an action, invent success or bypass clarifying questions |
| Correction/revocation | Update version/provenance; opt-out stops future writes and retrieval | Revoked item is immediately excluded |
| Export/deletion | User can inspect/export and delete one/all items; deletion covers durable records | Report failure honestly; do not claim deletion on an error |
| Expiry | Expired records are excluded and cleaned by explicit deterministic policy | Missing/invalid expiry rejected by schema validator |

## Threat model

- **Accidental disclosure:** a goal/plan in the current skill registry could contain personal context. The root ignore rules now exclude its runtime JSON and temporary file to reduce accidental commits; this does not encrypt the file or remove already-tracked data.
- **Over-learning from noisy STT:** one correction does not become global grammar or durable memory without explicit approval.
- **Prompt/data injection:** retrieved webpage text, model output and skill proposals are untrusted data; they are never instructions to grant consent.
- **Privilege escalation:** memory cannot enable skills. The existing validate+approve enable gate remains required.
- **Stale or wrong memory:** expiry, scope, provenance, confidence bounds and user review are required before retrieval.
- **Sensitive data:** credentials, secrets, clipboard contents, raw transcript history and full action arguments are excluded by default.

## M9 phase order and acceptance

- **M9.1 (completed):** inventory, source map, lifecycle/privacy matrix, proposed JSON schema, baseline tests and local-registry ignore guard; exact-SHA CI passed on `9fa8f8bde39611079e4bce170e77a955d8794432` in [run 39900778509](https://github.com/snchat78-svg/Vyom/actions/runs/39900778509).
- **M9.2 (completed):** explicit user opt-in, record-level approval, withdrawal and default-off writes passed exact-SHA [run 39901852967](https://github.com/snchat78-svg/Vyom/actions/runs/39901852967): 408 tests + 30 subtests.
- **M9.3 (next):** validated versioned local storage, provenance, confidence, scope, expiry, atomic writes and fail-closed load.
- **M9.3:** validated versioned storage, provenance, confidence, scope and expiry.
- **M9.4:** inspect/review, export, deletion and expiry cleanup.
- **M9.5:** safely integrate approved memories as hints only; prove no auto-enable/generated-code execution and pass combined exact-SHA audit.

M9.1 passed on `9fa8f8bde39611079e4bce170e77a955d8794432` in [run 39900778509](https://github.com/snchat78-svg/Vyom/actions/runs/39900778509), and M9.2 passed on `2401889a7efa0248736e196961063db160f09a6c` in [run 39901852967](https://github.com/snchat78-svg/Vyom/actions/runs/39901852967). The next phase is M9.3 versioned local memory storage; review/export/deletion is reserved for M9.4.
