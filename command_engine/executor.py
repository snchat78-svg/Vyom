"""
Project : Vyom AI
Version : 0.9.1
Module  : Executor

Purpose:
    Connect:

        User Command
            |
            v
        IntentEngine
            |
            +-----------------------------+
            |                             |
            | Known Intent                | Unknown Goal
            |                             |
            v                             v
        AutonomousAgent              AutonomousAgent
            |                             |
            v                             v
        ToolManager                ReasoningEngine
            |                             |
            v                             v
        Windows / Files /          CapabilityManager
        Applications                     |
                                         v
                                  Future Skill Builder

IMPORTANT:

    Existing IntentEngine and ToolManager behaviour is
    preserved.

    AutonomousAgent remains the main execution coordinator.

    IMPORTANT FIX:

    Number selections such as:

        1
        2
        3

    are NOT sent to AutonomousAgent as new goals when
    ToolManager has a pending selection.

    They are sent directly back to ToolManager so that
    SelectionManager can open the selected item.

    This preserves the existing application/file selection
    behaviour while allowing AutonomousAgent to handle
    unknown natural-language goals.

    Future versions will allow Vyom to create/learn new
    capabilities under controlled security and verification.
"""


from ai_core.brain import Brain

from ai_core.autonomous_agent import AutonomousAgent

from command_engine.intent import IntentEngine

from tools.tool_manager import ToolManager


# =========================================================
# CORE COMPONENTS
# =========================================================

brain = Brain()

intent_engine = IntentEngine()

tool_manager = ToolManager()

autonomous_agent = AutonomousAgent(
    tool_manager=tool_manager,
    brain=brain
)


# =========================================================
# CHECK PENDING SELECTION
# =========================================================

def _has_pending_selection():
    """
    Check whether ToolManager is currently waiting for
    the user to select a numbered result.

    Example:

        Vyom:
            Multiple items found:
            1. Notepad
            2. Notepad++
            3. Something else

            Please select a number.

        User:
            1

    In this situation '1' must go to ToolManager and NOT
    to AutonomousAgent.
    """

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


# =========================================================
# NORMALIZE AGENT RESULT
# =========================================================

def _result_to_message(
    result
):
    """
    Convert AutonomousAgent result into a normal Vyom
    response without losing useful information.
    """

    # -----------------------------------------------------
    # Normal string / other result
    # -----------------------------------------------------

    if not isinstance(
        result,
        dict
    ):

        return result

    # -----------------------------------------------------
    # Prefer actual ToolManager result.
    #
    # Example:
    #
    # {
    #     "success": True,
    #     "result": "Opened successfully: ..."
    # }
    # -----------------------------------------------------

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

    # -----------------------------------------------------
    # Agent message
    # -----------------------------------------------------

    message = result.get(
        "message"
    )

    if message is not None:

        return message

    # -----------------------------------------------------
    # Capability information
    #
    # Keep useful information visible instead of returning
    # an unreadable dictionary.
    # -----------------------------------------------------

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

    # -----------------------------------------------------
    # Missing capability
    # -----------------------------------------------------

    if result.get(
        "stage"
    ) == "missing_capability":

        return (
            "I do not currently have a capability "
            "for this task."
        )

    # -----------------------------------------------------
    # Safety limit
    # -----------------------------------------------------

    if result.get(
        "stage"
    ) == "safety_limit":

        return (
            "The autonomous task stopped because "
            "the maximum execution step limit was reached."
        )

    # -----------------------------------------------------
    # Execution error
    # -----------------------------------------------------

    if result.get(
        "stage"
    ) == "execution_error":

        error = result.get(
            "error",
            "Unknown execution error."
        )

        return (
            f"Task execution error: {error}"
        )

    # -----------------------------------------------------
    # Generic message fallback
    # -----------------------------------------------------

    return str(
        result
    )


# =========================================================
# EXECUTE
# =========================================================

def execute(
    command
):
    """
    Execute a user command.

    Main flow:

        Command
          |
          v
        IntentEngine
          |
          +-----------------------------+
          |                             |
       Selection                   Normal command
          |                             |
          v                             v
      ToolManager                AutonomousAgent
                                        |
                                        v
                                ReasoningEngine
                                        |
                         +--------------+--------------+
                         |                             |
                  Existing Tools                Capability
                         |                             |
                         v                             v
                   ToolManager              Future Skill System
    """

    # =====================================================
    # NORMALIZE COMMAND
    # =====================================================

    if command is None:

        return (
            "Please tell me what "
            "you want me to do."
        )

    command = str(
        command
    ).strip()

    if not command:

        return (
            "Please tell me what "
            "you want me to do."
        )

    # =====================================================
    # INTENT DETECTION
    # =====================================================

    try:

        intent = intent_engine.detect(
            command
        )

    except Exception as error:

        return (
            "Intent detection error: "
            f"{error}"
        )

    # =====================================================
    # NUMBER SELECTION FIX
    # =====================================================
    #
    # IMPORTANT:
    #
    # If ToolManager previously displayed:
    #
    #     1. Notepad
    #     2. Notepad++
    #
    # and user says:
    #
    #     1
    #
    # then '1' is a selection, not an autonomous goal.
    #
    # This must happen BEFORE AutonomousAgent.run().
    # =====================================================

    if command.isdigit():

        if _has_pending_selection():

            try:

                selection_intent = {
                    "intent": "unknown",
                    "target": command
                }

                result = tool_manager.execute(
                    selection_intent
                )

                return result

            except Exception as error:

                return (
                    "Selection error: "
                    f"{error}"
                )

    # =====================================================
    # AUTONOMOUS AGENT
    # =====================================================
    #
    # Existing known commands continue through the current
    # AutonomousAgent -> ReasoningEngine -> ToolManager path.
    #
    # Unknown natural-language goals also reach the
    # AutonomousAgent.
    #
    # Example known command:
    #
    #     open notepad
    #
    # Example unknown goal:
    #
    #     photo se data nikalkar excel bana do
    #
    # =====================================================

    try:

        result = autonomous_agent.run(
            goal=command,
            intent=intent
        )

    except Exception as error:

        return (
            "Autonomous execution error: "
            f"{error}"
        )

    # =====================================================
    # RETURN RESULT
    # =====================================================

    return _result_to_message(
        result
        )
