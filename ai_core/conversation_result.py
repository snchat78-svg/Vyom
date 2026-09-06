"""
Project : Vyom AI
Version : 1.0
Module  : Conversation Result

Purpose:
    Structured result container for conversation turns.
    Does NOT infer success by parsing human-readable strings.
"""

from dataclasses import dataclass
from typing import Optional, Dict, Any, List
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
    error_category: Optional[str] = None
    
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
            explicit_status = status_hint or result.get("status")
            
            if explicit_status:
                try:
                    status = ConversationStatus[str(explicit_status).upper()]
                except (KeyError, AttributeError):
                    status = ConversationStatus.SUCCESS if success else ConversationStatus.FAILED
            else:
                status = ConversationStatus.SUCCESS if success else ConversationStatus.FAILED
            
            return cls(
                status=status,
                response_text=response_text,
                executor_result=result,
                error_message=error_msg,
                error_category=result.get("error_category"),
                needs_selection=status == ConversationStatus.NEEDS_SELECTION,
                selection_options=result.get("selection_options"),
            )
        
        # Legacy executor paths return human-readable strings.  A normal
        # return means the call completed; this deliberately does not parse
        # response wording to decide an outcome.
        return cls(
            status=ConversationStatus.SUCCESS,
            response_text=str(result),
            executor_result={"raw": result},
            error_message=None
        )
