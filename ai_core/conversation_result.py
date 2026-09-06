"""
Project : Vyom AI
Version : 1.0
Module  : Conversation Result

Purpose:
    Structured result container for conversation turns.
    Does NOT infer success by parsing human-readable strings.
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any
from enum import Enum


class ConversationStatus(Enum):
    """Stable conversation outcome statuses."""
    SUCCESS = "success"
    NEEDS_SELECTION = "needs_selection"
    NEEDS_CLARIFICATION = "needs_clarification"
    REFUSED = "refused"
    FAILED = "failed"
    CANCELLED = "cancelled"
    EXIT_SESSION = "exit_session"


@dataclass
class ConversationResult:
    """Structured result from a conversation turn."""
    
    status: ConversationStatus
    response_text: str
    executor_result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    needs_selection: bool = False
    selection_options: Optional[list] = None
    
    @classmethod
    def from_executor_result(
        cls,
        result: Any,
        status_hint: Optional[str] = None
    ) -> "ConversationResult":
        """
        Safely convert executor.execute() result to ConversationResult.
        Does NOT infer success by parsing strings.
        Uses status_hint if provided.
        
        Args:
            result: Result from executor.execute()
            status_hint: Optional explicit status string
            
        Returns:
            ConversationResult with appropriate status
        """
        
        if result is None:
            return cls(
                status=ConversationStatus.FAILED,
                response_text="No response from executor",
                executor_result=None,
                error_message="Executor returned None"
            )
        
        if isinstance(result, dict):
            response_text = str(result.get("message", result.get("text", "")))
            error_msg = result.get("error", None)
            success = result.get("success", False)
            
            # Determine status
            if status_hint:
                try:
                    status = ConversationStatus[status_hint.upper()]
                except (KeyError, AttributeError):
                    status = ConversationStatus.SUCCESS if success else ConversationStatus.FAILED
            else:
                status = ConversationStatus.SUCCESS if success else ConversationStatus.FAILED
            
            return cls(
                status=status,
                response_text=response_text,
                executor_result=result,
                error_message=error_msg
            )
        
        # Fallback for non-dict results
        return cls(
            status=ConversationStatus.SUCCESS,
            response_text=str(result),
            executor_result={"raw": result},
            error_message=None
        )
