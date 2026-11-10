# Project Phase Continuity Standard

Use this file as a reusable workflow for **each project repository**. It is a template, not proof that other repositories already follow it. Copy/adapt it into each repository and link it from that repository's canonical phase-state file.

## Canonical files to maintain in each repository
- `docs/PHASE_STATE.md` (or the project's existing canonical equivalent): current in-progress phase, last verified completed phase, next incomplete phase, exact source/test SHA, CI run URL/result, known limitations, and next action.
- `docs/PHASE_CHECKPOINTS.md`: chronological phase evidence and completion audit.
- `docs/ROADMAP.md`: ordered phase plan and dependencies.
- Keep existing project filenames if they already serve these roles; do not create competing state files unnecessarily.

## Mandatory start-of-phase gate
1. Read the repository's canonical phase-state file **before making changes**.
2. Verify repository, active branch, current head SHA, recent commits, and latest CI run for the recorded code/test SHA.
3. Read the relevant checkpoint and roadmap sections. Check whether the requested phase is already complete or the work is already present.
4. If completed with exact-SHA passing CI, never repeat it. Continue with the next incomplete phase. If in progress and CI is red, fix that same phase rather than skipping ahead.
5. Record the active phase as IN PROGRESS before implementation, with scope and acceptance criteria.

## Mandatory completion gate
1. Add deterministic regression tests for the phase's acceptance criteria, including failure/edge cases.
2. Run the full project's required CI/tests on the exact commit containing the implementation and tests.
3. Only record COMPLETED when that exact SHA's run is successful. A commit message, merged code, syntax check alone, or an older run is not sufficient.
4. Update phase state, checkpoints, and roadmap with implementation/test SHA, CI URL, result/test counts if available, limitations, and the next phase.
5. Verify the documentation commit and leave an unambiguous handoff for the next chat.

## Rules against skipping and repetition
- The phase-state file is the source of truth for continuation. Do not rely only on chat history.
- Never mark a phase complete without passing exact-SHA CI.
- Never re-run/redo a completed phase unless a failing regression, new requirement, or explicit audit makes the revisit necessary; if revisited, record why.
- Do not skip incomplete dependencies to start a later phase.
- If a phase's CI fails, keep it in progress, fix the failure, add a regression test when warranted, and rerun CI.
- Do not claim hardware, microphone, production-network or interactive desktop behavior was validated unless it was actually tested in that environment.
- End every handoff with: last verified phase, current phase status, next phase, exact evidence links, and remaining limitations.

## Cross-chat / cross-project usage
- Each project needs its own durable state file in its own repository. Updating this template or one repository does not automatically update other repositories.
- At a new chat, start by reading that project's state file and verifying its latest CI. Never assume a phase status from a different project or chat.
- Use repository paths/links in the handoff so the next chat can resume without asking the user to repeat details.
