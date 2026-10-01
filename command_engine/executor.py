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
import re

from tools.tool_manager import ToolManager
from ai_core.response_engine import ResponseEngine
from ai_core.logger import log


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

def _natural_response(
    command,
    result,
    intent=None
):

    try:

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

        return response_engine.format(
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

    except Exception:

        return str(result)


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
    command
):

    # =========================================================
    # NORMALIZE COMMAND
    # =========================================================

    if command is None:

        return (
            "Please tell me what you want me to do."
        )

    command = str(
        command
    ).strip()

    if not command:

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

        autonomous_agent.reset()

        return (
            "Vyom session stopped."
        )

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

        intent = intent_engine.detect(
            command
        )

    except Exception as error:

        return (
            "Intent detection error: "
            +
            str(error)
        )

    if not isinstance(
        intent,
        dict
    ):

        intent = {
            "intent": "unknown",
            "target": command
        }

    log("[PIPELINE] INPUT -> INTENT: %s -> %s" % (command.encode("unicode_escape", errors="backslashreplace").decode("ascii"), str(intent.get("intent", "unknown"))))

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

    log("[PIPELINE] ROUTE PREVIEW: %s reason=%s" % (str(route_preview.get("route", "unknown")), str(route_preview.get("reason", ""))))

    if route_preview.get("route") == "goal":

        try:

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
            None
        )

    # =========================================================
    # CONTEXTUAL CLOSE
    # =========================================================

    if intent_type == "close_current":

        current_app = getattr(
            autonomous_agent.context,
            "current_app",
            None
        )

        if not current_app:

            return response_engine.failure_response(
                command,
                "No current application is available to close."
            )

        close_intent = {
            "intent": "close_app",
            "target": str(
                current_app
            )
        }

        try:

            raw = tool_manager.execute(
                close_intent
            )

            # Clear the application context only after an
            # actual close attempt.
            autonomous_agent.context.set_current_target(
                current_app
            )

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

        return response_engine.format(
            command=command,
            result={
                "success": True,
                "conversation_type": intent.get(
                    "conversation_type",
                    "acknowledge"
                )
            },
            intent=intent
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

            autonomous_agent.context.clear_pending_selection()

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
    # UNKNOWN SELECTION WITHOUT A PENDING LIST
    # =========================================================

    if (
        intent_type == "selection"
        and
        not _has_pending_selection()
    ):

        return response_engine.failure_response(
            command,
            "There is no pending selection to choose from."
        )

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

                return (
                    "ज़रूर। बताइए, क्या खोलना है?"
                )

            if intent_type == "search_file":

                return (
                    "ज़रूर। बताइए, कौन-सी फ़ाइल खोजनी है?"
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

                    return response_engine.failure_response(
                        command,
                        "No application was specified to close."
                    )

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

            raw_result = tool_manager.execute(
                intent
            )

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
    # EXTRACT MESSAGE
    # =========================================================

    message = _result_to_message(
        result
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

    return _natural_response(
        command,
        message,
        intent
    )
