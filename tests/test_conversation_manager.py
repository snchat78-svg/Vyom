"""
Project : Vyom AI
Module  : Conversation Manager Test

Purpose:
    Import and basic contract test only.
"""

from ai_core.conversation_manager import ConversationManager


def test_conversation_manager_import():
    manager = ConversationManager()

    assert manager.active is True
    assert manager.turn_count == 0
    assert manager.get_history() == []


if __name__ == "__main__":
    manager = ConversationManager()

    print("ConversationManager import: PASS")
    print(manager.snapshot())

