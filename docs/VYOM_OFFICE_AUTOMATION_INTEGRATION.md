# Vyom — Open-Source Office and Desktop Capability Integration

**Research/update date:** 2026-11-08  
**Repository:** snchat78-svg/Vyom  
**Branch:** updated  
**Phase boundary:** M10.4 remains in progress; this integration is an additive prototype, not M10.4 release acceptance.

## User goal

Vyom should understand Hindi, Roman Hindi, Hinglish and English instructions; answer questions; plan multi-step work; discover Windows applications, folders and files; operate general desktop software; and create, read, edit and save Microsoft Word, Excel and PowerPoint documents. It must verify results and ask for clarification when the goal or target is ambiguous.

No assistant can safely guarantee every possible command. Vyom must prefer grounded capabilities, explicit confirmation for high-impact operations and post-action verification over guessing.

## Research decision

### Microsoft UFO² — primary Office/Windows reference

Repository: https://github.com/microsoft/UFO  
License: MIT  
Relevant code reviewed:
- ufo/automator/app_apis/excel/excelclient.py
- ufo/automator/app_apis/word/wordclient.py
- ufo/automator/app_apis/powerpoint/powerpointclient.py
- ufo/automator/app_apis/factory.py
- ufo/client/mcp/local_servers/excel_wincom_mcp_server.py
- ufo/client/mcp/local_servers/word_wincom_mcp_server.py
- ufo/client/mcp/local_servers/ppt_wincom_mcp_server.py

The most useful pattern is application-specific native WinCOM receivers with GUI automation as a fallback. UFO² combines UI Automation, Win32 and Office COM/API execution. Its full desktop framework is not a drop-in dependency: current UFO² setup documentation specifies Windows 10 or newer and its full requirements list includes many frameworks that Vyom does not need.

**Decision:** do not transplant the entire UFO² agent runtime, MCP server stack, model orchestration, prompt system or large dependency set. Keep Vyom's own brain, planner, action schema, capability registry, mission runtime, risk policy, UIA and verification. Adapt the narrow application-specific COM boundary behind Vyom's CapabilityExecutor.

### Existing projects retained as design references

- Leon: skill/context and personal-assistant architecture; do not replace Vyom's Brain or memory lifecycle.
- Dodaios (formerly Personal Jarvis): desktop-agent orchestration patterns; do not add a second planner or executor.
- Open Interpreter: workspace scoping, review-before-destructive-action and computer-use concepts; do not allow generated code to bypass Vyom's validators.
- Shruti: optional Hindi/English/Hinglish STT feasibility candidate; Windows/target-device acceptance remains a separate gate.
- Existing pywinauto in requirements.txt and Vyom's current UIA stack remain the general GUI execution layer.

## Prototype implemented in this update

### New runtime provider

windows_agent/office_capability.py adds OfficeCOMCapability, registered from ai_core/ui_autonomous_agent.py alongside the existing WindowsUICapability.

The provider:
- imports COM support lazily and fails clearly when unavailable;
- opens Word, Excel and PowerPoint as visible applications;
- attaches to an existing Office instance when possible, otherwise starts one;
- defaults document opening to read-only;
- disables Excel macro execution during automation and prevents automatic external-link updates;
- exposes only a fixed list of JSON-data actions;
- verifies writes by reading back cells, text, table count or slide title/count;
- refuses creation over an existing destination and refuses Save As to a different existing path;
- limits range size, cell values, Word text/table sizes and PowerPoint slide text;
- does not execute Python, shell commands, VBA or model-generated scripts.

### Registered actions

| Action | Purpose |
|---|---|
| office_open_document | Open supported Word/Excel/PowerPoint documents; read-only by default |
| office_create_document | Create a new .docx, .xlsx or .pptx; never overwrite an existing file |
| office_read_document | Read active Word text, bounded Excel sheet data or bounded PowerPoint slide text |
| office_save_document | Save the active document; refuses a different existing destination |
| excel_read_range | Read a bounded A1-style cell range |
| excel_write_range | Write a bounded two-dimensional array and verify readback |
| word_append_text | Append plain text and verify document contents |
| word_replace_text | Replace text and compare the complete expected/read-back content |
| word_insert_table | Insert a bounded table and verify table count |
| powerpoint_add_slide | Add a slide with title/body placeholders and verify count/title |

This is an initial useful surface, not yet the complete Office feature set. It does not yet implement advanced formulas/charts/pivots, rich Word formatting, PowerPoint themes/images/animations, Outlook, arbitrary Office add-ins, or browser workflows.

### Current general Windows capability

Existing Vyom code remains responsible for:
- application and file/folder discovery/opening (UniversalAppLauncher, UniversalResolver, FileManager, ToolManager);
- UI Automation, keyboard/mouse, clipboard, window observation and verification (WindowsUICapability, UIStateObserver, UIVerificationEngine);
- semantic reasoning, planning, mission ordering and recovery (ReasoningEngine, MissionPlanner, MissionRuntime, AutonomousAgent).

Office COM is an additional capability for richer Office operations; it does not replace those systems.

## Safety and acceptance boundaries

1. All model output continues through Vyom's ActionValidator and CapabilityExecutor. Generated code is not an accepted action format.
2. Application UI remains visible so the user can supervise Office activity.
3. office_open_document is read-only unless the action explicitly requests read_only=false.
4. New file creation refuses an existing path. Saving as a different existing path is refused rather than silently overwriting.
5. Excel macros are forced disabled on the automation instance; external link updates are disabled.
6. Mutating actions must still be represented as explicit plan steps and pass Vyom's existing mission/risk/verification pipeline.
7. Unit tests use fake COM objects. They do not prove compatibility with an installed Office version.
8. Windows GitHub CI cannot prove that Word, Excel or PowerPoint are installed or activated on the user's PC.
9. UFO²'s complete framework documents Windows 10+ as its requirement. This small COM adapter is independent of UFO's runtime, but its compatibility with the user's specific Windows and Office versions must be tested. Vyom's current Python 3.11 package baseline remains Windows 8.1/version 6.3 or newer; Windows 8.0/version 6.2 is blocked.

## Test coverage added

tests/test_office_capability.py uses fake COM objects to cover provider registration surface, non-Windows fail-closed behavior, new-file overwrite protection, Excel readback, input bounds, Word append/replace/table verification and PowerPoint slide verification.

A green CI result means these contracts and the EXE build pass. It is not real Office acceptance.

## No-paid AI and screen perception extension (2026-11-08)

See [VYOM_FREE_LOCAL_AI_AND_SCREEN_PERCEPTION.md](VYOM_FREE_LOCAL_AI_AND_SCREEN_PERCEPTION.md) for the full design and future phases.

- ModelGateway now defaults to local Qwen and blocks all paid/cloud providers unless VYOM_ALLOW_PAID_API=true is explicitly enabled. The sample configuration sets it to false.
- The optional analyze_screen capability combines a coherent bounded UIA snapshot with an optional local-only vision model. Screenshots are sent only to literal loopback IPs, temporary BMP files are deleted, and model output is read-only observation data.
- Without local vision, Vyom uses UI Automation only. No Ollama/model is bundled or silently downloaded.
- Current Ollama Windows builds require Windows 10 22H2+. The previously recorded Windows 8/8.1, 2 GB target should use UIA-only mode; do not attempt to install the current Ollama runtime there.

## Remaining implementation roadmap

Do not skip the active M10.4 real-device acceptance gate. Once the supported target-device preflight/evidence is reviewed, continue in this order:

### M10.5 — Office and file-workflow capability expansion
1. Excel advanced work: formulas, formatting, tables, charts, filters and workbook analysis; validate every result.
2. Word advanced work: headings, styles, page layout, tables, images, citations and PDF export.
3. PowerPoint advanced work: themes, layouts, images, diagrams, charts, notes and slide review.
4. File/folder capability: list, search, read, create, copy, move and rename within user-authorized paths; deletion and bulk overwrite require explicit confirmation.
5. Cross-application workflows: gather data from files/web, create an Excel analysis, prepare a Word report and build a PowerPoint deck with dependency-aware plans and per-step verification.
6. General desktop workflows: use application discovery and UIA for applications without a native API; add app-specific providers only where native APIs clearly improve reliability.

### M10.6 — Broad task competence and real-world benchmark
1. Expand multilingual/noisy-STT intent and ambiguity corpus.
2. Build benign reversible end-to-end tasks spanning Explorer, browser, Office and common Windows applications.
3. Measure task completion, unsafe-guess rate, verification accuracy, latency and memory on the actual target PC.
4. Keep unsupported OS, unavailable applications, access-denied paths and ambiguous targets as explicit blocked/clarification outcomes—not false success.

## Source and license notes

Microsoft UFO is MIT licensed. Vyom uses an independent provider implementation informed by its Office COM receiver architecture; the full UFO codebase and runtime are not bundled. See THIRD_PARTY_NOTICES.md for the license notice.

## Current status

- [x] Inspect current Vyom capability/planner/UIA architecture.
- [x] Review Microsoft UFO² Office WinCOM code and license.
- [x] Add the first optional Office COM provider.
- [x] Register the provider through the existing capability executor.
- [x] Add mocked Office provider tests.
- [x] Exact-SHA Windows GitHub Actions acceptance for the provider/test commit `d7d2a6911fb78d6b0c2737a41529fea06b2c38c7` — [run 42455456449](https://github.com/snchat78-svg/Vyom/actions/runs/42455456449) passed 492 tests + 30 subtests, M10.2/M10.3 gates, EXE verification, CI-host smoke and artifact uploads.
- [ ] Target-device Office acceptance using installed Word, Excel and PowerPoint.
- [ ] Full M10.4 target-device preflight/manual evidence review.
- [ ] M10.5 must not be declared started/completed until M10.4 gate passes.
