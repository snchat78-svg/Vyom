"""
Project : Vyom AI
Module  : Conversation Manager Test

Purpose:
    Import and basic contract test only.
"""

from ai_core.conversation_manager import ConversationManager
from ai_core.conversation_result import ConversationResult, ConversationStatus


def test_conversation_manager_import():
    manager = ConversationManager()

    assert manager.active is True
    assert manager.turn_count == 0
    assert manager.get_history() == []

def test_needs_confirmation_is_a_distinct_conversation_status():
    result = ConversationResult.from_executor_result({
        "success": False,
        "status": "needs_confirmation",
        "stage": "recovery_confirmation_required",
        "message": "Check the current window and confirm.",
        "requires_user_input": True,
    })
    assert result.status == ConversationStatus.NEEDS_CONFIRMATION
    assert result.response_text == "Check the current window and confirm."


if __name__ == "__main__":
    manager = ConversationManager()

    print("ConversationManager import: PASS")
    print(manager.snapshot())

