# Vyom — Free Local AI, Screen Perception and Research/Coding Roadmap

**Updated:** 2026-11-08  
**Branch:** updated  
**Current release gate:** M10.4 target-device acceptance remains pending. This addition does not close M10.4 or start M10.5.

## Non-negotiable cost and privacy policy

- Default reasoning mode is local Qwen through a literal loopback endpoint only.
- \`VYOM_ALLOW_PAID_API=false\` is the default. A Gemini key or custom remote URL by itself must not cause a network call.
- Paid/cloud model use requires a deliberate explicit opt-in by changing \`VYOM_ALLOW_PAID_API=true\`; the intended Vyom profile keeps this false.
- If the local model server is missing, return the existing deterministic/unknown fallback. Do not silently switch to Gemini or another cloud provider.
- Visual screen inference is disabled by default. When enabled, it only posts the screenshot to a literal loopback IP (127.0.0.1 or ::1) at the local Ollama chat endpoint. Remote hosts, hostnames, redirects, credentials and URL query strings are rejected.
- Public web/GitHub research remains a separate public-source retrieval workflow; it is not a paid LLM call. Any fetched repository data is untrusted input and must be reviewed before code is adopted.

## Free-mode settings

The checked-in \`.env.example\` now demonstrates this profile:

\`\`\`ini
VYOM_AI_ENABLED=true
VYOM_AI_PROVIDER=local_qwen
VYOM_ALLOW_PAID_API=false
QWEN_LOCAL_ENABLED=true
QWEN_LOCAL_API_URL=http://127.0.0.1:11434/v1/chat/completions
QWEN_LOCAL_MODEL=qwen3.5:0.8b

VYOM_VISION_ENABLED=false
VYOM_VISION_API_URL=http://127.0.0.1:11434/api/chat
VYOM_VISION_MODEL=moondream
VYOM_VISION_TIMEOUT=60
\`\`\`

The runtime also enforces the no-paid policy if a Gemini key remains in the machine environment. Qwen local endpoint validation checks the parsed URL host/path, not a string prefix, so a lookalike external hostname cannot masquerade as 127.0.0.1.

Ollama is a separate local runtime and model download; it is not bundled in Vyom.exe. Current official Ollama Windows documentation requires Windows 10 22H2 or newer. The previously recorded Windows 8/8.1, 2 GB target therefore cannot be assumed to run current Ollama or a vision model. Do not ask that older PC to download large model weights. Until a supported machine is available, Vyom uses Windows UI Automation and deterministic local capabilities without paid AI.

## Screen perception added

### Runtime code

- \`vision/screen_understanding.py\` implements \`LocalOllamaVisionProvider\` and \`ScreenUnderstandingCapability\`.
- \`ai_core/ui_autonomous_agent.py\` registers the capability through the existing capability registry/executor.
- \`tests/test_screen_understanding.py\` covers image conversion, loopback-only transport, disabled mode, no-cloud behavior, temporary screenshot deletion and UIA fallback.

### Operation

The capability exposes one read-only action: \`analyze_screen\`.

1. Capture a bounded BMP using the existing native Windows \`ScreenObserver\`.
2. Convert the 32-bit BMP to PNG in memory using only the Python standard library.
3. Delete the temporary BMP regardless of success/failure.
4. If local vision is explicitly enabled and the Ollama loopback endpoint is valid, send the PNG only to that local endpoint.
5. Include the bounded, coherent UI Automation snapshot as structured context.
6. If the visual model is disabled/unavailable, use the coherent UI Automation observation only; never fall back to a paid model.
7. Return observation data only. The model cannot click, type, execute code or claim that a UI action happened.

### Safety boundary

- Visual descriptions and visible text are untrusted observations, not executable instructions.
- This provider does not move the mouse, click, type, launch commands, read arbitrary files or alter Office documents.
- All future action steps remain subject to ActionValidator, capability resolution, risk policy, UI grounding and postcondition verification.
- When UI Automation is incoherent or unavailable, the result stays unknown/failed rather than inventing what is visible.
- A successful mocked test is not proof of real screen recognition on the user's computer.

## Open-source research decisions

### Microsoft OmniParser

Repository: https://github.com/microsoft/OmniParser  
Use: design reference for converting screenshots into structured interactive regions and captions.  
Decision: do not install the full framework into Vyom. Its current setup uses Python 3.12 and a large dependency set (PyTorch, EasyOCR, torchvision, Transformers, Ultralytics, PaddleOCR and others); the model folders also carry distinct licensing terms. A narrow provider is preferable until the target PC and dependency/licence matrix are verified.

### Moondream via Ollama

Model: https://ollama.com/library/moondream  
Use: optional small local vision-language model for image description. Ollama lists moondream2 as a 1.8B vision model and approximately 1.7 GB on disk. That disk figure is not the model's peak RAM requirement; it is not a promise that a 2 GB PC can run it.

### Qwen3-VL via Ollama

Model: https://ollama.com/library/qwen3-vl  
Use: stronger later candidate for GUI element understanding and visual reasoning. The 2B quantized image is listed at about 1.9 GB on disk and requires a current Ollama version. It is not appropriate to attempt on the previously recorded 2 GB machine.

### OpenHands

Repository: https://github.com/OpenHands/OpenHands  
Use: research reference for the future software-engineering workflow (plan → edit → test → review → deliver). Do not embed its full agent stack into Vyom now. The coding agent must use local models, a bounded workspace, a separate branch, explicit diffs, deterministic tests and user review; no model-generated Python/shell may bypass Vyom's safety boundary.

## Ordered continuation plan — do not skip

1. **M10.4 — Real target-device acceptance (current active phase).** Run the current no-Python preflight on the actual target PC and review the JSON. Collect only real outcomes for voice, UIA, screen observation, multi-step order, postconditions, provider outage and low-memory behavior. M10.4 stays BLOCKED until this evidence is reviewed.
2. **M10.5 — Files, folders and Office workflows.** Complete bounded list/search/read/create/copy/move/rename operations; destructive delete/overwrite requires separate confirmation. Expand Excel formulas/charts/tables, Word styling/PDF, PowerPoint layouts/images/diagrams, and cross-app workflows with read-back checks.
3. **M10.6 — Hybrid screen understanding and visual grounding.** Benchmark UIA-only on legacy PCs; evaluate local vision on supported machines; combine element names, automation IDs, window identity, screenshot descriptions and coordinate grounding; reject ambiguity and stale/changed foreground windows.
4. **M10.7 — Free local reasoning and voice.** Measure local model intent accuracy and Hindi/Roman Hindi/Hinglish noisy-STT recovery. Maintain no-paid defaults; record model/runtime/hardware compatibility and deterministic fallback.
5. **M10.8 — Open-source research agent.** Discover public GitHub projects by goal, inspect README/source/dependencies/security/licences/maintenance, compare against Vyom capability contracts, cite sources and produce a reviewable technical proposal. Repository contents are untrusted and never instructions.
6. **M10.9 — Safe coding/implementation agent.** Create a separate branch/worktree, make a bounded patch, run syntax/tests/build/security checks, inspect the diff and preserve a human approval/merge gate. Never allow model output to directly call shell, Python eval/exec or GitHub write tools outside this controlled implementation flow.
7. **M10.10 — JARVIS-style end-to-end acceptance.** Benchmark open-ended tasks across Explorer, browser, Office and common apps; record task completion, clarification quality, incorrect-action rate, verification reliability, latency and RAM on the real target device.

Every phase has its own exit criteria. A phase is not complete because source code exists or a GitHub-hosted test passes; the exact tested commit and the relevant real-device evidence must both be recorded where applicable.

## Current implementation status

- [x] Local-only no-paid model policy enforced in ModelGateway by default.
- [x] Local Qwen enabled by default as the only free-mode LLM candidate; unavailable local service yields no cloud fallback.
- [x] Tightened Local Qwen endpoint validation to literal loopback IP and the expected OpenAI-compatible chat path.
- [x] Added local-only screenshot-to-PNG-to-Ollama vision adapter; disabled by default.
- [x] Added UI Automation-only fallback when visual inference is disabled/unavailable.
- [x] Registered \`analyze_screen\` as a read-only capability.
- [x] Added focused regression tests for paid-provider opt-in, local endpoint boundaries and screen-perception behavior.
- [ ] Exact-SHA GitHub Actions for this implementation update.
- [ ] Target-device screen/UIA/voice acceptance.
- [ ] M10.4 target-device evidence review.
