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
from tools.tool_manager import ToolManager


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
            # Keep task context alive
            # -------------------------------------------------

            try:

                if isinstance(
                    result,
                    str
                ):

                    result_lower = result.lower()

                    if (
                        "opened successfully"
                        in result_lower
                    ):

                        autonomous_agent.context.task_state = (
                            "active"
                        )

            except Exception:

                pass

            return result

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

    return _result_to_message(
        result
            )
