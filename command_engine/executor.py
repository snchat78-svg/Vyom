"""
Project : Vyom AI
Version : 1.0
Module  : Executor

Purpose:
    Connect:

        User Command
             |
             v
        IntentEngine
             |
             v
        Session State
             |
             +----------------------+
             |                      |
             v                      v
        Selection             AutonomousAgent
             |                      |
             v                      v
       ToolManager             ReasoningEngine
                                    |
                          +---------+---------+
                          |                   |
                          v                   v
                    Existing Tools      Capability System

Important:

    AutonomousAgent is created once and reused for the
    entire application session.

    This allows:

        command 1
        command 2
        command 3

    to share the same working context.

Example:

    open notepad
    one
    type hello
    save it

Security:

    This module does not execute arbitrary generated code.
"""


from ai_core.brain import Brain
from ai_core.autonomous_agent import AutonomousAgent
from command_engine.intent import IntentEngine
import re

from tools.tool_manager import ToolManager
from ai_core.response_engine import ResponseEngine


# =============================================================
# CORE COMPONENTS
# =============================================================

brain = Brain()

intent_engine = IntentEngine()

tool_manager = ToolManager()


# IMPORTANT:
#
# One persistent agent for the entire application session.
#
autonomous_agent = AutonomousAgent(
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
            selection_options=options
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

    # ---------------------------------------------------------
    # IntentEngine selection
    # ---------------------------------------------------------

    if isinstance(
        intent,
        dict
    ):

        selection = intent.get(
            "selection"
        )

        if selection is not None:

            return str(
                selection
            )

    text = str(
        command or ""
    ).strip().lower()

    # ---------------------------------------------------------
    # Direct number
    # ---------------------------------------------------------

    if text.isdigit():

        return text

    # ---------------------------------------------------------
    # English number words
    # ---------------------------------------------------------

    numbers = {

        "zero": "0",

        "one": "1",
        "first": "1",

        "two": "2",
        "second": "2",

        "three": "3",
        "third": "3",

        "four": "4",
        "fourth": "4",

        "five": "5",
        "fifth": "5",

        "six": "6",

        "seven": "7",

        "eight": "8",

        "nine": "9",

        "ten": "10"
    }

    if text in numbers:

        return numbers[text]

    # ---------------------------------------------------------
    # Prefix forms
    # ---------------------------------------------------------

    prefixes = [
        "number ",
        "option ",
        "item ",
        "choice ",
        "no "
    ]

    for prefix in prefixes:

        if text.startswith(
            prefix
        ):

            value = text[
                len(prefix):
            ].strip()

            if value.isdigit():

                return value

            if value in numbers:

                return numbers[value]

    # ---------------------------------------------------------
    # Hindi
    # ---------------------------------------------------------

    hindi_numbers = {

        "शून्य": "0",

        "एक": "1",
        "पहला": "1",
        "पहली": "1",

        "दो": "2",
        "दूसरा": "2",
        "दूसरी": "2",

        "तीन": "3",
        "तीसरा": "3",
        "तीसरी": "3",

        "चार": "4",
        "चौथा": "4",
        "चौथी": "4",

        "पांच": "5",
        "पाँच": "5"
    }

    if text in hindi_numbers:

        return hindi_numbers[text]

    # ---------------------------------------------------------
    # Natural selection phrases
    # ---------------------------------------------------------

    selection_phrases = {

        "पहला वाला": "1",
        "पहली वाली": "1",
        "पहले वाला": "1",
        "पहले वाली": "1",
        "पहला खोलो": "1",
        "पहला खोल दो": "1",

        "दूसरा वाला": "2",
        "दूसरी वाली": "2",
        "दूसरा खोलो": "2",
        "दूसरा खोल दो": "2",

        "तीसरा वाला": "3",
        "तीसरी वाली": "3",
        "तीसरा खोलो": "3",
        "तीसरा खोल दो": "3",

        "चौथा वाला": "4",
        "चौथी वाली": "4",

        "पांचवां वाला": "5",
        "पाँचवाँ वाला": "5",

        "first one": "1",
        "first one open": "1",
        "open the first": "1",
        "open the first one": "1",
        "first one please": "1",

        "second one": "2",
        "open the second": "2",
        "open the second one": "2",

        "third one": "3",
        "open the third": "3"
    }

    if text in selection_phrases:

        return selection_phrases[text]

    # Natural prefixes such as:
    # "open the first one", "पहला वाला खोल दो"
    normalized = re.sub(
        r"[^a-zA-Z0-9ऀ-ॿ ]+",
        " ",
        text
    )

    normalized = " ".join(
        normalized.split()
    )

    if normalized in selection_phrases:

        return selection_phrases[normalized]

    return None


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
    # INTENT
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

    intent_type = str(
        intent.get(
            "intent",
            "unknown"
        )
    ).strip().lower()

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
    #
    # Simple known commands should NOT pay the full
    # AutonomousAgent -> ReasoningEngine -> Plan route.
    #
    # These operations are deterministic and are already
    # implemented by ToolManager.
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
    #
    # Only genuinely unknown or non-deterministic goals
    # go through the AutonomousAgent.
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

