# Vyom Open-Source Assistant Integration Assessment

**Research date:** 2026-11-08  
**Repository:** `snchat78-svg/Vyom`  
**Branch inspected:** `updated`  
**Branch head at review:** `df22648871cc5de28fb21d60e5054fe2e40e7341`  
**Current project gate:** M10.4 — Real Windows integration and release exit gate; target-device evidence is still blocked.

## Executive decision

There is no single maintained open-source GitHub project that should replace Vyom end-to-end as a drop-in JARVIS. The strongest overall conceptual match is **Leon 2.0**, but its new `develop` branch is explicitly a Developer Preview and its new documentation is incomplete. The most promising small component for Vyom's Hindi/English/Hinglish voice path is **Shruti**, but the project's own integration guide says Windows has not been tested on any route. Neither should be copied wholesale into the production branch.

**Recommended architecture:** keep Vyom's existing Brain, meaning/intent engine, planner, mission runtime, world state, UI automation, verification and safety contracts. Introduce external projects only behind narrow, replaceable provider/capability adapters after Windows compatibility and target-device tests pass.

## Current Vyom surfaces inspected

- `voice/speech_to_text.py` currently uses SpeechRecognition and the `recognize_google` request path, with Hindi/English language fallback. This makes the STT layer the clearest opportunity for an offline provider.
- `voice/text_to_speech.py` already uses Windows SAPI/pyttsx3 and local eSpeak NG fallback for Hindi. A new TTS engine is optional, not a prerequisite.
- `voice/voice_controller.py` shares the existing conversation/executor path and manages wake/utterance/audio handoff.
- `ai_core/meaning_intent_engine.py`, `goal_compiler.py`, `mission_planner.py`, `mission_runtime.py`, `world_state.py`, and `autonomous_agent.py` already own intent, planning, state and recovery.
- `windows_agent/` already contains UI automation, element finding/grounding, screen observation, window/process control and UI verification.
- `ai_core/web_knowledge.py` already handles sourced web answers and unknown/conflict outcomes.

This is why a replacement assistant core would overlap heavily with code already present and could bypass the current verification and recovery contracts.

## Candidate comparison

| Project | What it offers | Fit with Vyom | Decision |
|---|---|---|---|
| [Leon](https://github.com/leon-ai/leon) | Personal assistant organized around tools, context, memory, native/agent skills and desktop/browser computer use | Closest whole-assistant/JARVIS concept; major architecture overlap | Study as architecture reference. Do not replace Vyom with its 2.0 preview |
| [Shruti](https://github.com/udgamlabs/shruti) | Small offline speech models for Hindi + English + Hinglish; native C engine and ONNX packages | Best candidate to evaluate for the current STT gap and low-memory target | Prototype only after Windows/OS compatibility checks; do not ship as default yet |
| [Vosk](https://github.com/alphacep/vosk-api) | Offline streaming speech recognition; small Hindi model and Indian-English model | Simple fallback candidate with Windows bindings; published comparative Hindi/Hinglish results are materially weaker than Shruti's own benchmark | Keep as a baseline/fallback experiment, not the preferred Hinglish recognizer |
| [whisper.cpp](https://github.com/ggml-org/whisper.cpp) | Native C/C++ Whisper with Windows builds, CPU inference and quantization | Useful multilingual comparison engine; likely a larger runtime/model footprint than a small specialist model | Optional benchmark on a more capable device; don't assume it fits 2 GB RAM |
| [OpenVoiceOS](https://github.com/OpenVoiceOS/ovos-core) | Modular voice-assistant platform with separate listener, core, audio/TTS and skill services | Good voice-service/skill architecture, but not Vyom's Windows desktop executor | Borrow service boundaries or a specific plugin if needed; don't transplant the full platform |
| [Open Interpreter](https://github.com/openinterpreter/openinterpreter) | Coding/terminal agent with Windows support, sandbox modes and approval policies | Possible isolated file/code-workspace tool; not a complete personal voice assistant | Consider only behind a separate least-privilege tool adapter; never bypass Vyom's mission/approval checks |
| [Microsoft UFO²](https://github.com/microsoft/UFO) | Windows desktop agent combining UI Automation, Win32/WinCOM and GUI actions | Strong desktop-agent concept; overlaps with Vyom's existing UIA/grounding layer | Do not integrate into the current target: UFO² quick start requires Windows 10 or newer |
| [Piper](https://github.com/OHF-Voice/piper1-gpl) | Local neural TTS, including Hindi voice models | Optional alternative to current eSpeak NG/SAPI | Review GPL-3.0 engine and each voice model's separate license before distributing with Vyom |

## Important Shruti findings

The Shruti repository describes 22 language-specific models, with each model covering its language, English and mixed speech. The Hindi model file is about 29.5 MB and is explicitly intended for Hindi, English and Hinglish. Its weights and Python ONNX package are Apache-2.0.

However, the repository also states:
- Windows has **not been run on any Shruti integration route**.
- The native Cactus engine route is the smallest/fastest route in the published phone test, but integrating the C library is more involved.
- The Python ONNX 4-bit route downloads about 32 MB but uses roughly 0.8–1 GB after loading on the measured Mac.
- The ONNX int8 route uses roughly 120 MB on the measured Mac, but the repository marks the Hindi ONNX builds as failed in its comparison against the native engine.
- The Hindi ONNX route, long-audio behavior, low-resource Windows behavior and actual microphone latency must be tested on the target PC before production use.

The project authors' own 18–19 October 2026 comparison reports Shruti at 20.46 WER on Monsoon Hindi and 35.21 on MUCS Hinglish; Vosk small (Hindi + Indian English) at 35.75 and 61.14 respectively. These are the authors' published test results, not an independent Vyom benchmark. Results do not prove performance on Vyom's microphone, dialect, Windows build or hardware.

## OS and hardware blocker

The current Vyom M10.4 register says the Python 3.11 baseline requires Windows 8.1/version 6.3 or newer; Windows 8.0/version 6.2 is unsupported. The user previously described a Windows 8, 64-bit, 2 GB RAM PC. The exact OS version must be confirmed before adding a new native runtime. Even a 30 MB model file does not mean the full inference stack will fit or run on that PC.

## Recommended integration order (do not skip M10.4)

1. Complete M10.4 target-device preflight/evidence on a supported Windows version. Confirm the actual Windows version and available RAM first.
2. Add an STT provider boundary that preserves Vyom's existing transcript/result schema. Keep current provider behavior intact behind a feature flag.
3. Build an offline test harness using public/synthetic Hindi, Roman Hindi, Hinglish, Indian-English and noisy-transcription clips. Measure word/command error, false activation, latency, peak RAM and CPU on the real target.
4. Compare Shruti native engine, Shruti ONNX int8 (only if its Hindi result is acceptable), Vosk small and whisper.cpp. Do not select based only on model file size or vendor benchmark numbers.
5. Enable one provider as an optional backend only after exact-SHA CI and target-device acceptance. Preserve fallback, microphone lifecycle and transcript provenance.
6. Consider Piper only as a separate TTS provider after Hindi voice-model licensing and memory/latency are checked. Keep current eSpeak NG/SAPI fallback.
7. Keep external desktop/code agents (UFO²/Open Interpreter) isolated behind existing capability validation, explicit confirmations and postcondition verification. They must not own Vyom's planner or execute around MissionRuntime.

## Sources reviewed

- Leon README and current `develop` branch architecture: https://github.com/leon-ai/leon and https://github.com/leon-ai/leon/blob/develop/core/context/ARCHITECTURE.md
- OpenVoiceOS core and service installation: https://github.com/OpenVoiceOS/ovos-core and https://github.com/OpenVoiceOS/OpenVoiceOS
- Open Interpreter Windows and sandbox/approval documentation: https://www.openinterpreter.com/docs/desktop/install and https://www.openinterpreter.com/docs/sandbox
- Microsoft UFO² requirements and quick start: https://github.com/microsoft/UFO/blob/main/documents/docs/getting_started/quick_start_ufo2.md
- Shruti README, comparative results, integration guide and limitations: https://github.com/udgamlabs/shruti, https://github.com/udgamlabs/shruti/blob/main/docs/comparison.md, https://github.com/udgamlabs/shruti/blob/main/onnx/docs/integrate.md, https://github.com/udgamlabs/shruti/blob/main/onnx/docs/limits.md
- Vosk, whisper.cpp and Piper: https://github.com/alphacep/vosk-api, https://github.com/ggml-org/whisper.cpp, https://github.com/OHF-Voice/piper1-gpl

## Final status

**Research complete; no third-party runtime or model has been installed or integrated.** M10.4 remains the active Vyom phase. Shruti is the first STT candidate for a controlled Windows feasibility test, while Leon is the closest overall architecture reference. No phase is skipped or marked complete by this research note.
