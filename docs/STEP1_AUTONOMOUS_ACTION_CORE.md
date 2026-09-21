Vyom Step 1 — Autonomous Action Core v1.0
Verified baseline
This package was prepared against the updated branch of snchat78-svg/Vyom, using the actual repository files as the source of truth.
Confirmed existing execution path:
Goal → GoalCompiler → ReasoningEngine → MissionPlanner → MissionRuntime → ToolManager
The existing Windows opening stack remains outside this patch:
ToolManager → UniversalAppLauncher / UniversalResolver / ProcessManager
No launcher, resolver, process manager, voice engine, or autonomous-agent file is replaced by Step 1.
Existing open functionality checked before Step 1
The current branch already contains the implementation needed for the existing deterministic opening behaviour:
open is routed by tools/tool_manager.py through the universal target path.
open_file and search/open continue to use UniversalResolver.
tools/universal_resolver.py contains PDF, JPG and JPEG file extensions and uses Windows launch fallbacks including os.startfile, ShellExecuteW, and cmd.exe.
tools/universal_app_launcher.py contains normal file/folder opening plus Windows application discovery through Start Menu, AppsFolder/AUMID, registry/path sources, and multiple launch fallbacks.
This is a code-level source audit of the current branch. Actual application/PDF launching cannot be executed on the Linux build environment used for this package, so no Windows runtime success is claimed here.
Because those capabilities already exist, Step 1 does not reimplement them.
What Step 1 adds
Step 1 adds the missing generic action protocol needed before Windows UI, Office, browser and coding capabilities can be built safely.
New modules:
ai_core/action_schema.py — provider-agnostic generic action data contract.
ai_core/action_validator.py — schema, safety, dependency and cycle validation.
ai_core/capability_registry.py — dynamic capability metadata registry.
ai_core/capability_resolver.py — resolves a generic action to an advertised capability; never executes it.
Updated modules:
ai_core/reasoning_gateway.py — accepts validated generic actions without enumerating every future action name.
ai_core/reasoning_engine.py — carries generic actions through the reasoning layer and routes them to capability/missing-capability handling without translating them into legacy intents.
ai_core/mission_planner.py — preserves generic action fields in the mission plan while keeping the existing legacy mission format.
ai_core/model_gateway.py — tells the reasoning model to emit data-only generic actions and never executable code.
.github/workflows/vyom.yml — checks the new modules and runs the full offline test suite before packaging the EXE.
Generic action contract
{
  "id": "action_1",
  "action": "click_control",
  "capability": "windows_ui",
  "target": "Save",
  "args": {},
  "preconditions": ["window is focused"],
  "postconditions": ["save operation is triggered"],
  "depends_on": []
}
There is deliberately no master allowlist of future action names in the generic protocol. The action is a structured identifier. A capability provider advertises which operations it supports, and the resolver decides whether a provider exists.
Existing legacy path remains separate
The existing execute_existing_intent path remains the compatibility format for the current ToolManager execution stack.
The old execution safety guard in ReasoningEngine is retained for those legacy intents because the current ToolManager only supports its existing intent contract.
A new generic action such as click_control is not silently converted to open, open_file, or another legacy intent. That conversion would create hard-coded coupling and would make future capabilities difficult to add.
Safety boundary
AI output remains data only.
Step 1 rejects executable implementation fields such as Python/source/script/callable/tool-object payloads inside generic actions.
Generic actions are validated for:
valid identifiers;
JSON-safe arguments and metadata;
maximum plan size;
unique action IDs;
known dependencies;
self-dependencies;
dependency cycles.
No generic action is executed by Step 1.
Tests performed
Targeted Step 1 suite:
16 tests — PASS
Also run:
Python bytecode compilation for all Step 1 Python files — PASS.
Package contents checked to ensure no __pycache__/.pyc files are included.
The test suite covers generic schema validation, future action-name flexibility, safety filtering, dependency-cycle detection, dynamic capability registration/resolution, generic AI gateway validation, legacy compatibility, mission-plan normalization, generic-action routing, mixed-plan partial-execution protection, and the unchanged simple legacy path.
Full existing repository tests and a Windows EXE runtime launch were not executed in this Linux environment. The updated GitHub Actions workflow now makes the full offline test suite a prerequisite for EXE packaging.
Files intentionally not changed
These existing working modules are not included in the Step 1 patch:
ai_core/autonomous_agent.py
tools/tool_manager.py
tools/universal_app_launcher.py
tools/universal_resolver.py
tools/file_manager.py
windows_agent/process_manager.py
voice/*
memory/session_memory.py
This is intentional: Step 1 should build the generic cognitive/action contract, not rewrite working computer-opening code.
Next step
Step 2 — Windows UI / Computer Control
The next implementation should provide the first real generic capability executor behind this protocol: window discovery/focus, keyboard, hotkeys, click/double-click, typing, clipboard, observation and verification.
Existing open app, file/folder, JPG/JPEG/PDF behaviour should remain intact while that capability is added.
