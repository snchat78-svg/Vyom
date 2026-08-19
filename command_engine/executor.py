"""
Project : Vyom AI
Version : 0.9
Module  : Executor

Purpose:
    Connect:

        User Command
            |
            v
        IntentEngine
            |
            v
        AutonomousAgent
            |
            v
        ToolManager
            |
            v
        Windows / Files / Applications

IMPORTANT:

    Existing IntentEngine and ToolManager behaviour is
    preserved.

    AutonomousAgent is now the execution coordinator.

    Future versions will allow the Agent to understand
    commands that do not exist in the fixed IntentEngine.
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
# EXECUTE
# =========================================================

def execute(command):
    """
    Execute a user command.

    Current flow:

        Command
          ↓
        IntentEngine
          ↓
        AutonomousAgent
          ↓
        ToolManager
          ↓
        Result
    """

    # -----------------------------------------------------
    # Normalize command
    # -----------------------------------------------------

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

    intent = intent_engine.detect(
        command
    )

    # =====================================================
    # AUTONOMOUS AGENT
    # =====================================================

    result = autonomous_agent.run(
        goal=command,
        intent=intent
    )

    # =====================================================
    # RETURN RESULT
    # =====================================================

    if isinstance(
        result,
        dict
    ):

        # -------------------------------------------------
        # Prefer actual ToolManager result.
        # -------------------------------------------------

        if (
            "result" in result
            and result.get(
                "result"
            ) is not None
        ):

            return result.get(
                "result"
            )

        # -------------------------------------------------
        # Otherwise return Agent message.
        # -------------------------------------------------

        return result.get(
            "message",
            result
        )

    return result
