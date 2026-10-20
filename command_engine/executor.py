"""
Project : Vyom AI
Version : 1.1
Module  : Executor

Purpose:
    Connect the user-facing command/voice layer to Vyom's persistent
    AutonomousAgent while preserving the existing deterministic fast paths.

Step 2 change:
    The session now uses UIAutonomousAgent. That subclass intercepts only
    generic Action Schema steps. Existing open/file/search/close handling
    remains on ToolManager exactly as before.
"""

from ai_core.brain import Brain
from ai_core.ui_autonomous_agent import UIAutonomousAgent
from command_engine.intent import IntentEngine
from ai_core.goal_router import GoalRouter
import hashlib
import re

from tools.tool_manager import ToolManager
from ai_core.response_engine import ResponseEngine
from ai_core.logger import log
from ai_core.result_schema import normalize_result


# =============================================================
# CORE COMPONENTS
# =============================================================

brain = Brain()

intent_engine = IntentEngine()
goal_router = GoalRouter()

tool_manager = ToolManager()


# IMPORTANT:
#
# One persistent agent for the entire application session.
#
# UIAutonomousAgent preserves the base AutonomousAgent contract and adds
# generic Windows UI capability execution without replacing the existing
# ToolManager/application/file/process stack.
autonomous_agent = UIAutonomousAgent(
    tool_manager=tool_manager,
    brain=brain
)

response_engine = ResponseEngine()


def _trace_sink_update(trace_sink, **values):
    """Write compact telemetry to the active conversation turn, when supplied."""
    if isinstance(trace_sink, dict):
        trace_sink.update(values)


def _trace_intent(trace_sink, intent):
    if not isinstance(trace_sink, dict) or not isinstance(intent, dict):
        return
    target = str(intent.get("target") or "").strip()
    hypotheses = intent.get("hypotheses")
    if not isinstance(hypotheses, list):
        hypotheses = intent.get("alternatives")
    confidence = intent.get("confidence")
    compact = {
        "type": str(intent.get("intent") or "unknown")[:80],
        "target_present": bool(target),
        "selection_present": bool(str(intent.get("selection") or "").strip()),
        "hypothesis_count": min(16, len(hypotheses)) if isinstance(hypotheses, list) else 0,
    }
    if isinstance(confidence, (int, float)) and not isinstance(confidence, bool):
        try:
            value = float(confidence)
            if 0.0 <= value <= 1.0 and value == value and value not in (float("inf"), float("-inf")):
                compact["confidence"] = round(value, 4)
        except (TypeError, ValueError, OverflowError):
            pass
    trace_sink["intent"] = compact


# =============================================================
# CHECK PENDING SELECTION
# =============================================================

def _has_pending_selection():

    try:

        selection_manager = getattr(
            tool_manager,
            "selection_manager",
            None
        )

        if selection_manager is None:

            return False

        has_results = getattr(
            selection_manager,
            "has_results",
            None
        )

        if callable(
            has_results
        ):

            return bool(
                has_results()
            )

    except Exception:

        pass

    return False


# =============================================================
# SYNC PENDING SELECTION WITH SESSION CONTEXT
# =============================================================

def _sync_pending_selection_context(target=None):

    try:

        selection_manager = getattr(
            tool_manager,
            "selection_manager",
            None
        )

        if selection_manager is None:
            return

        if selection_manager.has_results():

            results = list(
                getattr(
                    selection_manager,
                    "results",
                    []
                )
            )

            if target is None:

                target = getattr(
                    tool_manager,
                    "selection_source",
                    None
                )

            autonomous_agent.context.set_pending_selection(
                target,
                results
            )

        else:

            autonomous_agent.context.clear_pending_selection()

    except Exception:
        pass


# =============================================================
# NATURAL RESPONSE
# =============================================================

def _structured_response(
    message,
    *,
    success,
    stage,
    status=None,
    result=None,
    error=None,
):
    payload = {
        "success": bool(success),
        "status": status or ("success" if success else "failed"),
        "stage": str(stage or ("completed" if success else "failed")),
        "message": str(message or ""),
        "response": str(message or ""),
        "result": result,
    }
    if error is not None:
        payload["error"] = str(error)
    return normalize_result(
        payload,
        default_stage=payload["stage"],
        status_hint=payload["status"],
    )


def _failure_response(command, raw_result, stage="failed"):
    message = response_engine.failure_response(command, raw_result)
    return _structured_response(
        message,
        success=False,
        stage=stage,
        status="failed",
        result=raw_result,
    )


def _recovery_confirmation_response(command, recovery, metadata=None):
    recovery = recovery if isinstance(recovery, dict) else {}
    kind = str(recovery.get("kind") or "unclear")
    source_result = recovery.get("source_result")
    voice_metadata = metadata
    if voice_metadata is None and isinstance(source_result, dict):
        voice_metadata = (
            {"voice": source_result.get("voice")}
            if isinstance(source_result.get("voice"), dict) else None
        )
    language = response_engine.detect_language(command, metadata=voice_metadata)
    if response_engine._explicit_english_request(command):
        language = "english"

    prompts = {
        "english": (
            "I couldn't verify whether the action took effect, so I have not repeated it. "
            "Check the current window and reply with one clear choice: "
            "'already happened' (stop without replay), "
            "'did not happen; retry' (take a fresh UI observation, then retry and verify), "
            "or 'cancel recovery' (stop without retry). A plain yes/no is not enough."
        ),
        "hindi": (
            "मैं यह सत्यापित नहीं कर पाया कि action हुआ या नहीं, इसलिए उसे दोबारा नहीं किया है। "
            "वर्तमान window जाँचकर इनमें से एक स्पष्ट जवाब दें: "
            "'हो गया' (दोबारा नहीं करूँगा), 'नहीं हुआ, दोबारा करो' (नई UI observation लेकर retry और verification करूँगा), "
            "या 'रहने दो' (बिना retry mission रोक दूँगा)। केवल हाँ/नहीं पर्याप्त नहीं है।"
        ),
        "hinglish": (
            "Main verify nahi kar paya ki action hua ya nahi, isliye usse repeat nahi kiya. "
            "Current window check karke clear reply dein: 'ho gaya' (repeat nahi hoga), "
            "'nahi hua, dobara karo' (fresh UI observation ke baad retry + verify), "
            "ya 'rehne do' (retry ke bina mission stop). Sirf yes/no kaafi nahi hai."
        ),
    }
    if kind == "restart_retry_unavailable":
        category = str(
            recovery.get("recovery_lock_category") or ""
        )
        if category == "recovery_journal_unreadable":
            messages = {
                "english": (
                    "Vyom found a recovery marker it could not safely read, so it has paused new actions. "
                    "Check the current window. Reply 'already happened' only if you independently confirmed it, "
                    "or 'cancel recovery' to stop without replay. Automatic retry is disabled."
                ),
                "hindi": (
                    "Vyom को recovery marker सुरक्षित रूप से पढ़ने में समस्या मिली है, इसलिए नए actions रोक दिए हैं। "
                    "वर्तमान window जाँचें। केवल स्वयं पुष्टि करने पर 'हो गया' कहें, या बिना दोबारा चलाए रोकने के लिए "
                    "'रहने दो' कहें। Automatic retry बंद है।"
                ),
                "hinglish": (
                    "Vyom recovery marker ko safely read nahi kar paya, isliye naye actions pause hain. "
                    "Current window check karein. Khud confirm kiya ho tabhi 'ho gaya' bolein, ya bina replay ke "
                    "rokne ke liye 'rehne do' bolein. Automatic retry disabled hai."
                ),
            }
        else:
            messages = {
                "english": (
                    "A recovery marker from the previous Vyom session was found, but the original mission plan "
                    "was intentionally not stored. Vyom cannot safely retry it after restart. Check the current "
                    "window, then reply 'already happened' only if confirmed, or 'cancel recovery' to stop without replay."
                ),
                "hindi": (
                    "पिछले Vyom session का recovery marker मिला है, लेकिन सुरक्षा के लिए पुराना mission plan सेव नहीं किया गया था। "
                    "Restart के बाद Vyom इसे सुरक्षित रूप से retry नहीं कर सकता। Current window जाँचें; पुष्टि होने पर ही "
                    "'हो गया' कहें, या बिना replay रोकने के लिए 'रहने दो' कहें।"
                ),
                "hinglish": (
                    "Pichhle Vyom session ka recovery marker mila, lekin safety ke liye original mission plan save nahi tha. "
                    "Restart ke baad Vyom isse safely retry nahi kar sakta. Current window check karein; confirm ho tabhi "
                    "'ho gaya' bolein, ya bina replay rokne ke liye 'rehne do' bolein."
                ),
            }
        response = _structured_response(
            messages[language],
            success=False,
            stage="recovery_confirmation_required",
            status="needs_confirmation",
            result={"requires_user_input": True, "retry_available": False},
        )
        response["requires_user_input"] = True
        response["recovery_options"] = ["already_applied", "cancel"]
        response["error_category"] = "recovery_restored_after_restart"
        return response

    if kind in {"unclear", "observation_unavailable"}:
        message = prompts[language]
        if kind == "observation_unavailable":
            extra = {
                "english": " The live UI state is unavailable or stale, so no retry was sent.",
                "hindi": " Live UI state उपलब्ध नहीं थी या पुरानी थी, इसलिए कोई retry नहीं किया गया।",
                "hinglish": " Live UI state available nahi thi ya stale thi, isliye retry nahi kiya.",
            }
            message += extra[language]
        elif recovery.get("retry_hint"):
            extra = {
                "english": " Please use one of the explicit replies above.",
                "hindi": " कृपया ऊपर दिए गए स्पष्ट जवाबों में से एक दें।",
                "hinglish": " Upar diye gaye clear replies mein se ek dein.",
            }
            message += extra[language]
        response = _structured_response(
            message, success=False, stage="recovery_confirmation_required",
            status="needs_confirmation", result={"requires_user_input": True},
        )
        response["requires_user_input"] = True
        response["recovery_options"] = ["already_applied", "not_applied_retry", "cancel"]
        response["error_category"] = "uncertain_action_outcome"
        return response

    if kind == "already_applied":
        messages = {
            "english": "Thanks for confirming. I will not repeat that action. The previous mission is stopped; this is user-confirmed, not machine-verified.",
            "hindi": "पुष्टि के लिए धन्यवाद। मैं उस action को दोबारा नहीं करूँगा। पुराना mission रोक दिया है; यह आपकी पुष्टि है, system द्वारा verified result नहीं।",
            "hinglish": "Confirm karne ke liye thanks. Main action repeat nahi karunga. Purana mission stop hai; ye aapki confirmation hai, system-verified result nahi.",
        }
        return _structured_response(
            messages[language], success=False, stage="recovery_resolved_applied",
            status="failed", result={"resolution": "user_confirmed_applied"},
        )

    if kind == "cancelled":
        messages = {
            "english": "Recovery cancelled. The previous mission is stopped and the uncertain action was not repeated.",
            "hindi": "Recovery रद्द कर दी गई है। पुराना mission रोक दिया गया है और उस अनिश्चित action को दोबारा नहीं किया।",
            "hinglish": "Recovery cancel kar di. Purana mission stop hai aur uncertain action repeat nahi kiya.",
        }
        return _structured_response(
            messages[language], success=False, stage="recovery_cancelled",
            status="cancelled", result={"resolution": "cancelled_without_replay"},
        )

    if kind == "retry_result":
        execution = recovery.get("execution_result")
        execution = execution if isinstance(execution, dict) else {}
        if execution.get("stage") == "recovery_confirmation_required":
            nested = _recovery_confirmation_response(command, {
                "kind": "observation_unavailable"
                if execution.get("failure_policy", {}).get("category") == "recovery_observation_unavailable"
                else "unclear",
                "source_result": execution,
            }, metadata)
            return nested
        if recovery.get("success") is True:
            messages = {
                "english": "You confirmed the action had not happened. I took a fresh UI observation, retried, and the mission completed with verification.",
                "hindi": "आपने पुष्टि की कि action नहीं हुआ था। नई UI observation लेकर retry किया और mission verification के साथ पूरा हुआ।",
                "hinglish": "Aapne confirm kiya ki action nahi hua tha. Fresh UI observation ke baad retry kiya aur mission verification ke saath complete hua.",
            }
            return _structured_response(
                messages[language], success=True, stage="recovery_retry_completed",
                status="success", result={"verified": True, "resolution": "confirmed_not_applied_then_retried"},
            )
        messages = {
            "english": "The confirmed retry did not complete the mission. Vyom stopped safely; check the current window before deciding the next step.",
            "hindi": "पुष्टि के बाद किया गया retry mission पूरा नहीं कर पाया। Vyom सुरक्षित रूप से रुक गया है; आगे के कदम से पहले current window जाँचें।",
            "hinglish": "Confirm kiye gaye retry se mission complete nahi hua. Vyom safely ruk gaya hai; agla step lene se pehle current window check karein.",
        }
        return _structured_response(
            messages[language], success=False, stage="recovery_retry_failed",
            status="failed", result={"verified": False, "resolution": "confirmed_replay_failed"},
        )

    return _structured_response(
        "Recovery state could not be resolved.", success=False,
        stage="recovery_confirmation_required", status="needs_confirmation",
        result={"requires_user_input": True},
    )


def _natural_response(
    command,
    result,
    intent=None
):

    try:

        if isinstance(result, dict) and result.get("stage") == "recovery_confirmation_required":
            return _recovery_confirmation_response(
                command,
                {
                    "kind": "observation_unavailable"
                    if result.get("failure_policy", {}).get("category") == "recovery_observation_unavailable"
                    else "unclear",
                    "source_result": result,
                },
                metadata={"voice": intent.get("voice", {})} if isinstance(intent, dict) and isinstance(intent.get("voice"), dict) else None,
            )

        options = None

        selection_manager = getattr(
            tool_manager,
            "selection_manager",
            None
        )

        if selection_manager is not None:

            if selection_manager.has_results():

                options = list(
                    getattr(
                        selection_manager,
                        "results",
                        []
                    )
                )

        message = response_engine.format(
            command=command,
            result=result,
            intent=intent,
            selection_options=options,
            context=(
                autonomous_agent.context.snapshot()
                if hasattr(autonomous_agent, "context")
                else {}
            ),
        )

        if isinstance(result, dict):
            payload = dict(result)
            success = bool(payload.get("success", False))
            payload["success"] = success
            payload["status"] = str(
                payload.get("status")
                or ("success" if success else "failed")
            )
            payload["stage"] = str(
                payload.get("stage")
                or ("completed" if success else "failed")
            )
            payload["message"] = str(message or "")
            payload["response"] = str(message or "")
            return normalize_result(
                payload,
                default_stage=payload["stage"],
                status_hint=payload["status"],
            )

        return _structured_response(
            message,
            success=True,
            stage="legacy_completed",
            status="success",
            result=result,
        )

    except Exception as error:

        return _failure_response(
            command,
            error,
            stage="response_formatting_error",
        )


# =============================================================
# NORMALIZE SELECTION
# =============================================================

def _get_selection_number(
    command,
    intent
):

    # The IntentEngine is the single source of truth for selection parsing.
    # This prevents the voice path and normal command path from interpreting
    # "number 1 kholo", "1 open", etc. differently.
    if isinstance(intent, dict):
        selection = intent.get("selection")
        if selection is not None:
            value = str(selection).strip()
            if value:
                return value

    try:
        detected = intent_engine._detect_selection(
            str(command or "")
        )
    except Exception:
        detected = None

    if detected is not None:
        value = str(detected).strip()
        if value:
            return value

    text = str(command or "").strip()
    return text if text.isdigit() else None



# =============================================================
# RESULT TO MESSAGE
# =============================================================

def _result_to_message(
    result
):

    # ---------------------------------------------------------
    # Normal string / other result
    # ---------------------------------------------------------

    if not isinstance(
        result,
        dict
    ):

        return result

    # ---------------------------------------------------------
    # Actual ToolManager result
    # ---------------------------------------------------------

    if (
        "result" in result
        and
        result.get(
            "result"
        ) is not None
    ):

        return result.get(
            "result"
        )

    # ---------------------------------------------------------
    # Agent message
    # ---------------------------------------------------------

    message = result.get(
        "message"
    )

    if message is not None:

        return message

    # ---------------------------------------------------------
    # Capability not implemented
    # ---------------------------------------------------------

    if result.get(
        "stage"
    ) == "capability_not_implemented":

        capability = result.get(
            "capability",
            {}
        )

        if isinstance(
            capability,
            dict
        ):

            capability_name = capability.get(
                "name",
                "unknown"
            )

        else:

            capability_name = str(
                capability
            )

        return (
            "I identified the required capability "
            f"'{capability_name}', but its executor "
            "is not implemented yet."
        )

    # ---------------------------------------------------------
    # Skill plan
    # ---------------------------------------------------------

    if result.get(
        "stage"
    ) in (
        "skill_planned",
        "capability_planned"
    ):

        return (
            "I analyzed the goal and created "
            "a capability plan."
        )

    # ---------------------------------------------------------
    # Safety limit
    # ---------------------------------------------------------

    if result.get(
        "stage"
    ) == "safety_limit":

        return (
            "I stopped the task safely because "
            "the execution limit was reached."
        )

    # ---------------------------------------------------------
    # Execution error
    # ---------------------------------------------------------

    if result.get(
        "stage"
    ) == "execution_error":

        return (
            "I could not complete that action: "
            +
            str(
                result.get(
                    "error",
                    "unknown error"
                )
            )
        )

    # ---------------------------------------------------------
    # Reasoning error
    # ---------------------------------------------------------

    if result.get(
        "stage"
    ) == "reasoning_error":

        return (
            "I could not reason through that task: "
            +
            str(
                result.get(
                    "error",
                    "unknown reasoning error"
                )
            )
        )

    # ---------------------------------------------------------
    # Generic fallback
    # ---------------------------------------------------------

    return str(
        result
    )


# =============================================================
# EXECUTE
# =============================================================

def execute(
    command,
    metadata=None,
    trace_sink=None,
):

    # =========================================================
    # NORMALIZE COMMAND
    # =========================================================

    if command is None:
        _trace_sink_update(trace_sink, routing_path="input_validation")

        return _structured_response(
            "Please tell me what you want me to do.",
            success=False,
            stage="needs_clarification",
            status="needs_clarification",
        )

    command = str(
        command
    ).strip()

    if not command:
        _trace_sink_update(trace_sink, routing_path="input_validation")

        return (
            "Please tell me what you want me to do."
        )

    # =========================================================
    # EXIT SESSION
    # =========================================================

    if command.lower() in (
        "exit",
        "quit",
        "shutdown vyom",
        "close vyom"
    ):
        _trace_sink_update(trace_sink, routing_path="exit_session")

        autonomous_agent.reset()

        return _structured_response(
            "Vyom session stopped.",
            success=True,
            stage="exit_session",
            status="exit_session",
        )

    # Resolve any uncertain prior action before normal intent/goal routing.
    recovery_handler = getattr(
        autonomous_agent,
        "handle_recovery_confirmation",
        None,
    )
    if callable(recovery_handler):
        recovery = recovery_handler(command)
        if recovery is not None:
            _trace_sink_update(trace_sink, routing_path="recovery_confirmation")
            return _recovery_confirmation_response(command, recovery, metadata)

    # =========================================================
    # GOAL / COMMAND ROUTING
    # =========================================================

    # =========================================================
    # INTENT
    #
    # Detect after voice normalization so the goal router receives the
    # semantic command metadata instead of a raw pre-normalization surface.
    # =========================================================

    try:

        if metadata is not None:
            intent = intent_engine.detect(
                command,
                metadata=metadata,
            )
        else:
            intent = intent_engine.detect(command)

    except Exception as error:

        return _failure_response(
            command,
            "Intent detection error: " + str(error),
            stage="intent_detection_error",
        )

    if not isinstance(
        intent,
        dict
    ):

        intent = {
            "intent": "unknown",
            "target": command
        }

    _trace_intent(trace_sink, intent)
    log("[PIPELINE] INPUT -> INTENT: %s -> %s" % (command.encode("unicode_escape", errors="backslashreplace").decode("ascii"), str(intent.get("intent", "unknown"))))

    # =========================================================
    # PENDING SELECTION HAS ABSOLUTE PRIORITY
    # =========================================================
    # A pending result list is active working state. A spoken "ek", "one",
    # "number 1", etc. must select from that list, never become a fresh
    # semantic goal.
    selection_number = _get_selection_number(command, intent)
    if selection_number is not None and _has_pending_selection():
        try:
            selection_intent = {
                "intent": "unknown",
                "target": str(selection_number),
                "voice": intent.get("voice", {}) if isinstance(intent, dict) else {},
            }
            result = tool_manager.execute(selection_intent)
            _sync_pending_selection_context()
            return _natural_response(
                command,
                result,
                selection_intent,
            )
        except Exception as error:
            return response_engine.failure_response(
                command,
                str(error),
            )

    # =========================================================
    # GOAL / COMMAND ROUTING
    # =========================================================

    try:

        route_preview = goal_router.route(
            command,
            intent=intent,
        )

    except Exception:

        route_preview = {
            "route": "command",
            "reason": "router_error",
            "goal": False,
        }

    _trace_sink_update(
        trace_sink,
        route={
            "name": str(route_preview.get("route") or "unknown")[:80],
            "reason": str(route_preview.get("reason") or "")[:120],
            "goal": bool(route_preview.get("goal")),
        },
    )
    log("[PIPELINE] ROUTE PREVIEW: %s reason=%s" % (str(route_preview.get("route", "unknown")), str(route_preview.get("reason", ""))))

    if route_preview.get("route") == "goal":
        _trace_sink_update(trace_sink, routing_path="autonomous_goal")

        try:

            # A goal must be interpreted from the complete utterance.
            # The deterministic IntentEngine result is parser metadata only;
            # passing a partial "open" intent here could collapse a compound
            # mission into its first action.
            result = autonomous_agent.run(
                goal=command,
                intent=None,
            )

        except Exception as error:

            return _failure_response(command, str(error), stage="executor_error")

        _sync_pending_selection_context(command)

        return _natural_response(
            command,
            result,
            intent,
        )

    # Intent has already been detected above.

    intent_type = str(
        intent.get(
            "intent",
            "unknown"
        )
    ).strip().lower()

    # =========================================================
    # UNKNOWN -> SEMANTIC GOAL PATH
    #
    # "unknown" is not a failed command. It means the deterministic
    # parser did not decide the meaning. Give the complete utterance
    # to the semantic reasoning layer instead of returning a robot-like
    # unknown result or trying to add another phrase rule.
    # =========================================================

    if intent_type == "unknown":
        _trace_sink_update(trace_sink, routing_path="semantic_goal")

        try:
            # Preserve the parser's unknown classification as metadata only.
            # AutonomousAgent/semantic reasoning must decide the actual
            # meaning; no legacy intent is created from it.
            result = autonomous_agent.run(
                goal=command,
                intent=intent,
            )
        except Exception as error:
            return response_engine.failure_response(
                command,
                str(error)
            )

        _sync_pending_selection_context(command)

        log("[PIPELINE] SEMANTIC RESULT: stage=%s success=%s" % (str(result.get("stage", "")) if isinstance(result, dict) else "", str(result.get("success", "")) if isinstance(result, dict) else ""))

        return _natural_response(
            command,
            result,
            intent
        )

    # =========================================================
    # CONTEXTUAL CLOSE
    # =========================================================

    if intent_type == "close_current":

        # Prefer the actual foreground window over stale remembered app/file
        # names. This is what lets "PDF khol diya -> close" close the window
        # that is actually on screen, even when the opened file is not a
        # process name.
        active_window = {}
        try:
            snapshot = autonomous_agent.world_state.snapshot(
                autonomous_agent.context.snapshot(),
                mission_state=autonomous_agent.mission_runtime.snapshot(),
                include_ui=True,
                include_clipboard=False,
            )
            active_window = snapshot.get("current_window") or {}
            if not active_window:
                active_window = (
                    snapshot.get("ui", {}).get("active_window", {})
                    if isinstance(snapshot.get("ui"), dict)
                    else {}
                )
        except Exception:
            active_window = {}

        current_app = getattr(
            autonomous_agent.context,
            "current_app",
            None
        )
        current_file = getattr(
            autonomous_agent.context,
            "current_file",
            None
        )

        target = str(
            active_window.get("title")
            or current_app
            or current_file
            or ""
        ).strip()
        hwnd = active_window.get("hwnd")

        if not target and not hwnd:

            return response_engine.failure_response(
                command,
                "No current window is available to close."
            )

        close_intent = {
            "intent": "close_app",
            "target": target,
        }

        try:
            capability_executor = getattr(
                autonomous_agent,
                "capability_executor",
                None,
            )

            execute_capability = getattr(
                capability_executor,
                "execute",
                None,
            )

            if callable(execute_capability):
                close_action = {
                    "action": "close_application",
                    "capability": "windows_ui",
                    "target": target,
                    "args": {},
                }
                if hwnd:
                    close_action["args"]["hwnd"] = hwnd
                raw = execute_capability(close_action)
            else:
                raw = tool_manager.execute(close_intent)

            if isinstance(raw, dict) and raw.get("success"):
                try:
                    autonomous_agent.context.last_success = True
                    autonomous_agent.context.last_result = raw
                except Exception:
                    pass

            return _natural_response(
                command,
                raw,
                close_intent
            )

        except Exception as error:

            return response_engine.failure_response(
                command,
                str(error)
            )

    # =========================================================
    # CONVERSATION
    # =========================================================

    if intent_type == "conversation":
        _trace_sink_update(trace_sink, routing_path="conversation")

        return _natural_response(
            command,
            {
                "success": True,
                "conversation_type": intent.get(
                    "conversation_type",
                    "conversation"
                )
            },
            intent,
        )

    # =========================================================
    # SELECTION
    # =========================================================

    selection_number = (
        _get_selection_number(
            command,
            intent
        )
    )

    if (
        selection_number is not None
        and
        _has_pending_selection()
    ):

        try:

            selection_intent = {
                "intent": "unknown",
                "target": str(
                    selection_number
                )
            }

            result = tool_manager.execute(
                selection_intent
            )

            # Keep the pending list alive when a number was invalid;
            # successful selection clears it inside ToolManager.
            _sync_pending_selection_context()

            # Keep the successful selection in current context.
            if isinstance(
                result,
                str
            ):

                lowered = result.lower()

                if (
                    "opened successfully" in lowered
                    or "opened windows application" in lowered
                ):

                    selected_name = (
                        autonomous_agent.context.selection_target
                        or autonomous_agent.context.current_target
                    )

                    if selected_name:

                        autonomous_agent.context.set_current_app(
                            selected_name
                        )

            return _natural_response(
                command,
                result,
                selection_intent
            )

        except Exception as error:

            return response_engine.failure_response(
                command,
                str(error)
            )

    # =========================================================
    # SELECTION IS CONTEXTUAL, NOT A GLOBAL COMMAND CLASS
    # =========================================================
    # Numbers are only selections when a selection list is actually pending.
    # Otherwise the complete utterance must remain available to semantic
    # reasoning (for example arithmetic or another natural-language task).
    if (
        intent_type == "selection"
        and
        not _has_pending_selection()
    ):
        intent = {
            "intent": "unknown",
            "target": command,
            "voice": intent.get("voice", {}) if isinstance(intent, dict) else {},
        }
        intent_type = "unknown"

    # =========================================================
    # FAST LANE
    # =========================================================

    fast_intents = {
        "open",
        "open_file",
        "search_file",
        "search_and_open_file",
        "close_app"
    }

    if intent_type in fast_intents:
        _trace_sink_update(trace_sink, routing_path="deterministic_fast_lane")

        target = str(
            intent.get(
                "target",
                ""
            ) or ""
        ).strip()

        # -----------------------------------------------------
        # Missing target
        # -----------------------------------------------------

        if not target:

            if intent_type == "open":

                return _structured_response(
                    "ज़रूर। बताइए, क्या खोलना है?",
                    success=False,
                    stage="needs_clarification",
                    status="needs_clarification",
                )

            if intent_type == "search_file":

                return _structured_response(
                    "ज़रूर। बताइए, कौन-सी फ़ाइल खोजनी है?",
                    success=False,
                    stage="needs_clarification",
                    status="needs_clarification",
                )

            if intent_type == "close_app":

                current_app = getattr(
                    autonomous_agent.context,
                    "current_app",
                    None
                )

                if current_app:

                    intent = {
                        "intent": "close_app",
                        "target": str(
                            current_app
                        )
                    }

                else:

                    return _failure_response(command, "No application was specified to close.", stage="needs_clarification")

        try:

            # Record current context before execution.
            autonomous_agent.context.set_current_target(
                intent.get(
                    "target",
                    ""
                )
            )

            if intent_type == "open":

                autonomous_agent.context.set_current_app(
                    intent.get(
                        "target",
                        ""
                    )
                )

            elif intent_type in (
                "open_file",
                "search_file",
                "search_and_open_file"
            ):

                autonomous_agent.context.set_current_file(
                    intent.get(
                        "target",
                        ""
                    )
                )

            raw_result = None

            # For an explicit close target, prefer the live generic UI
            # capability when the target resolves to an observed window.
            # This avoids treating document-viewer processes (for example a
            # PDF opened by an associated application) as if the document
            # filename itself were a Windows process name.
            if intent_type == "close_app":
                try:
                    capability_executor = getattr(
                        autonomous_agent,
                        "capability_executor",
                        None,
                    )
                    execute_capability = getattr(
                        capability_executor,
                        "execute",
                        None,
                    )
                    if callable(execute_capability):
                        ui_snapshot = autonomous_agent.world_state.snapshot(
                            autonomous_agent.context.snapshot(),
                            mission_state=autonomous_agent.mission_runtime.snapshot(),
                            include_ui=True,
                            include_clipboard=False,
                        )
                        active_window = ui_snapshot.get("current_window") or {}
                        active_title = str(active_window.get("title") or "").strip()
                        target_text = str(intent.get("target") or "").strip()
                        live_match = bool(
                            active_window.get("hwnd")
                            and target_text
                            and (
                                target_text.lower() in active_title.lower()
                                or active_title.lower() in target_text.lower()
                            )
                        )
                        if live_match:
                            close_action = {
                                "action": "close_application",
                                "capability": "windows_ui",
                                "target": active_title or target_text,
                                "args": {"hwnd": active_window.get("hwnd")},
                            }
                            candidate = execute_capability(close_action)
                            if isinstance(candidate, dict) and candidate.get("success"):
                                raw_result = candidate
                except Exception:
                    raw_result = None

            if raw_result is None:
                if intent_type == "open" and isinstance(tool_manager, ToolManager):
                    log(
                        "[EXEC] STRUCTURED APP OPEN START: %s"
                        % str(intent.get("target") or "").encode(
                            "unicode_escape", errors="backslashreplace"
                        ).decode("ascii")
                    )
                    raw_result = tool_manager.execute(
                        intent,
                        structured=True,
                    )
                    log(
                        "[EXEC] STRUCTURED APP OPEN END: success=%s stage=%s"
                        % (
                            str(raw_result.get("success", False))
                            if isinstance(raw_result, dict) else "unknown",
                            str(raw_result.get("stage", "legacy"))
                            if isinstance(raw_result, dict) else "legacy",
                        )
                    )
                else:
                    raw_result = tool_manager.execute(intent)

            # -------------------------------------------------
            # Sync selection state immediately.
            # -------------------------------------------------

            _sync_pending_selection_context(
                intent.get(
                    "target"
                )
            )

            return _natural_response(
                command,
                raw_result,
                intent
            )

        except Exception as error:

            return response_engine.failure_response(
                command,
                str(error)
            )

    # =========================================================
    # NATURAL / COMPLEX GOAL
    # =========================================================

    try:

        result = autonomous_agent.run(
            goal=command,
            intent=intent
        )

    except Exception as error:

        return response_engine.failure_response(
            command,
            str(error)
        )

    # =========================================================
    # SYNC SELECTION
    # =========================================================

    selection_target = (
        intent.get(
            "target"
        )
        if isinstance(
            intent,
            dict
        )
        else None
    )

    _sync_pending_selection_context(
        selection_target
    )

    # =========================================================
    # NATURAL RESPONSE
    # =========================================================
    # Preserve the complete structured autonomous result so ConversationManager
    # can report the real execution status instead of treating its human
    # response text as a new successful command.
    return _natural_response(
        command,
        result,
        intent
    )
