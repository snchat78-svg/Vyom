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

        return "Vyom session stopped."

    # =========================================================
    # INTENT DETECTION
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

    # =========================================================
    # INCOMPLETE / CONTEXTUAL COMMANDS
    # =========================================================

    if isinstance(intent, dict) and intent.get("intent") == "open":
        if not str(intent.get("target") or "").strip():
            if re.search(r"[\u0900-\u097F]", command):
                return "ज़रूर। बताइए, क्या खोलना है?"
            return "Sure. What would you like me to open?"

    if isinstance(intent, dict) and intent.get("intent") == "open_current":
        current_target = (
            getattr(autonomous_agent.context, "current_app", None)
            or getattr(autonomous_agent.context, "current_file", None)
            or getattr(autonomous_agent.context, "current_target", None)
        )

        if not current_target:
            if re.search(r"[\u0900-\u097F]", command):
                return "अभी मेरे पास कोई पिछला ऐप या फ़ाइल नहीं है जिसे मैं फिर से खोल सकूँ।"
            return "I don't have a previous app or file to reopen yet."

        intent = {
            "intent": "open",
            "target": str(current_target)
        }

    if isinstance(intent, dict) and intent.get("intent") == "search":
        if not str(intent.get("target") or "").strip():
            if re.search(r"[\u0900-\u097F]", command):
                return "ज़रूर। क्या खोजूँ?"
            return "Sure. What would you like me to search for?"

    # =========================================================
    # CONTEXTUAL CLOSE
    # =========================================================

    if isinstance(intent, dict) and intent.get("intent") == "close_current":
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
            "target": str(current_app)
        }

        try:
            raw = tool_manager.execute(close_intent)
            return _natural_response(command, raw, close_intent)
        except Exception as error:
            return response_engine.failure_response(command, str(error))

    # =========================================================
    # SIMPLE CONVERSATION
    # =========================================================

    if isinstance(intent, dict) and intent.get("intent") == "conversation":
        return response_engine.format(
            command=command,
            result={
                "success": True,
                "conversation_type": intent.get("conversation_type", "acknowledge")
            },
            intent=intent
        )

    # =========================================================
    # SELECTION DETECTION
    # =========================================================

    selection_number = (
        _get_selection_number(
            command,
            intent
        )
    )

    # =========================================================
    # PENDING SELECTION
    #
    # VERY IMPORTANT:
    #
    # If ToolManager is waiting for:
    #
    #     1. Notepad
    #     2. Notepad++
    #
    # and user says:
    #
    #     one
    #
    # then this is NOT a new autonomous goal.
    #
    # It must go directly to ToolManager.
    # =========================================================

    if (
        selection_number is not None
        and
        _has_pending_selection()
    ):

        try:

            selection_intent = {
                "intent": "unknown",
                "target": selection_number
            }

            result = tool_manager.execute(
                selection_intent
            )

            # -------------------------------------------------
            # Selection consumed
            # -------------------------------------------------

            try:

                autonomous_agent.context.clear_pending_selection()

            except Exception:

                pass

            # -------------------------------------------------
            # Natural conversational response
            # -------------------------------------------------

            return _natural_response(
                command,
                result,
                selection_intent
            )

        except Exception as error:

            return (
                "Selection error: "
                +
                str(error)
            )

    # =========================================================
    # NORMAL AUTONOMOUS EXECUTION
    # =========================================================

    try:

        result = autonomous_agent.run(
            goal=command,
            intent=intent
        )

    except Exception as error:

        return (
            "Autonomous execution error: "
            +
            str(error)
        )

    # =========================================================
    # RETURN NORMAL USER RESPONSE
    # =========================================================

    message = _result_to_message(
        result
    )

    # If ToolManager created a selection, preserve it in
    # SessionContext and let ResponseEngine explain it naturally.
    selection_target = (
        intent.get("target")
        if isinstance(intent, dict)
        else None
    )

    _sync_pending_selection_context(
        selection_target
    )

    return _natural_response(
        command,
        message,
        intent
    )
