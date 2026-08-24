"""
Project : Vyom AI
Version : 1.0
Module  : Session Memory

Purpose:
    Maintain Vyom's temporary working memory for the
    current conversation/session.

This is NOT long-term memory.

It remembers:
    - current goal
    - last instruction
    - current application
    - current file
    - current target
    - pending selection
    - last action
    - last result
    - task history
    - conversation context
    - confirmation state

Security:
    SessionMemory cannot modify security, permissions,
    core files, or execute generated code.
"""


from typing import Any, Dict, List, Optional


class SessionMemory:

    def __init__(self):

        # =====================================================
        # SESSION
        # =====================================================

        self.active = True

        # =====================================================
        # CURRENT TASK
        # =====================================================

        self.current_goal = ""

        self.last_instruction = ""

        self.task_state = "idle"

        self.current_step = 0

        # =====================================================
        # CURRENT CONTEXT
        # =====================================================

        self.current_app: Optional[str] = None

        self.current_file: Optional[str] = None

        self.current_target: Optional[str] = None

        # =====================================================
        # LAST ACTION
        # =====================================================

        self.last_action: Optional[Dict[str, Any]] = None

        self.last_result: Any = None

        self.last_success: Optional[bool] = None

        # =====================================================
        # SELECTION
        # =====================================================

        self.pending_selection = False

        self.selection_target: Optional[str] = None

        self.selection_options: List[Any] = []

        # =====================================================
        # CONFIRMATION
        # =====================================================

        self.awaiting_confirmation = False

        self.confirmation_reason: Optional[str] = None

        # =====================================================
        # CONVERSATION HISTORY
        # =====================================================

        self.conversation_history: List[
            Dict[str, Any]
        ] = []

        # =====================================================
        # TASK HISTORY
        # =====================================================

        self.task_history: List[
            Dict[str, Any]
        ] = []

    # =========================================================
    # START / CONTINUE
    # =========================================================

    def start_task(
        self,
        instruction: str,
        preserve_context: bool = True
    ):

        instruction = str(
            instruction or ""
        ).strip()

        if not instruction:
            return

        if not preserve_context:
            self.clear_task()

        self.current_goal = instruction

        self.last_instruction = instruction

        self.task_state = "active"

        self.current_step = 0

        self.add_message(
            "user",
            instruction
        )

    # =========================================================
    # MESSAGE
    # =========================================================

    def add_message(
        self,
        role: str,
        text: str,
        metadata: Optional[
            Dict[str, Any]
        ] = None
    ):

        self.conversation_history.append(
            {
                "role": str(role),
                "text": str(text),
                "metadata": metadata or {}
            }
        )

        if len(
            self.conversation_history
        ) > 100:

            self.conversation_history = (
                self.conversation_history[-100:]
            )

    # =========================================================
    # ACTION
    # =========================================================

    def record_action(
        self,
        action: Dict[str, Any]
    ):

        self.current_step += 1

        self.last_action = action

    # =========================================================
    # RESULT
    # =========================================================

    def record_result(
        self,
        result: Any,
        success: bool
    ):

        self.last_result = result

        self.last_success = bool(
            success
        )

        self.task_history.append(
            {
                "step": self.current_step,
                "action": self.last_action,
                "result": result,
                "success": bool(success)
            }
        )

        if len(
            self.task_history
        ) > 100:

            self.task_history = (
                self.task_history[-100:]
            )

    # =========================================================
    # CURRENT APP
    # =========================================================

    def set_current_app(
        self,
        app: Optional[str]
    ):

        if app:

            self.current_app = (
                str(app).strip()
            )

    # =========================================================
    # CURRENT FILE
    # =========================================================

    def set_current_file(
        self,
        file_path: Optional[str]
    ):

        if file_path:

            self.current_file = (
                str(file_path).strip()
            )

    # =========================================================
    # CURRENT TARGET
    # =========================================================

    def set_current_target(
        self,
        target: Optional[str]
    ):

        if target:

            self.current_target = (
                str(target).strip()
            )

    # =========================================================
    # PENDING SELECTION
    # =========================================================

    def set_pending_selection(
        self,
        target: Optional[str] = None,
        options: Optional[List[Any]] = None
    ):

        self.pending_selection = True

        self.selection_target = (
            str(target).strip()
            if target
            else None
        )

        self.selection_options = (
            list(options)
            if options
            else []
        )

        self.task_state = (
            "waiting_for_selection"
        )

    # =========================================================
    # CLEAR SELECTION
    # =========================================================

    def clear_pending_selection(self):

        self.pending_selection = False

        self.selection_target = None

        self.selection_options = []

        if self.task_state == (
            "waiting_for_selection"
        ):

            self.task_state = "active"

    # =========================================================
    # CONFIRMATION
    # =========================================================

    def request_confirmation(
        self,
        reason: str
    ):

        self.awaiting_confirmation = True

        self.confirmation_reason = str(
            reason
        )

        self.task_state = (
            "waiting_for_confirmation"
        )

    # =========================================================
    # CLEAR CONFIRMATION
    # =========================================================

    def clear_confirmation(self):

        self.awaiting_confirmation = False

        self.confirmation_reason = None

        if self.task_state == (
            "waiting_for_confirmation"
        ):

            self.task_state = "active"

    # =========================================================
    # COMPLETE
    # =========================================================

    def mark_completed(self):

        self.task_state = "completed"

    # =========================================================
    # FAILED
    # =========================================================

    def mark_failed(self):

        self.task_state = "failed"

    # =========================================================
    # CONTEXT CHECK
    # =========================================================

    def has_context(self) -> bool:

        return bool(
            self.current_goal
            or self.current_app
            or self.current_file
            or self.current_target
            or self.pending_selection
            or self.last_action
        )

    # =========================================================
    # SNAPSHOT
    # =========================================================

    def snapshot(self):

        return {
            "active": self.active,
            "current_goal": self.current_goal,
            "last_instruction": self.last_instruction,
            "task_state": self.task_state,
            "current_step": self.current_step,

            "current_app": self.current_app,
            "current_file": self.current_file,
            "current_target": self.current_target,

            "last_action": self.last_action,
            "last_result": self.last_result,
            "last_success": self.last_success,

            "pending_selection": self.pending_selection,
            "selection_target": self.selection_target,
            "selection_options": list(
                self.selection_options
            ),

            "awaiting_confirmation": (
                self.awaiting_confirmation
            ),

            "confirmation_reason": (
                self.confirmation_reason
            ),

            "conversation_history": list(
                self.conversation_history
            ),

            "task_history": list(
                self.task_history
            )
        }

    # =========================================================
    # CLEAR CURRENT TASK
    # =========================================================

    def clear_task(self):

        self.current_goal = ""

        self.last_instruction = ""

        self.task_state = "idle"

        self.current_step = 0

        self.current_app = None

        self.current_file = None

        self.current_target = None

        self.last_action = None

        self.last_result = None

        self.last_success = None

        self.pending_selection = False

        self.selection_target = None

        self.selection_options = []

        self.awaiting_confirmation = False

        self.confirmation_reason = None

        self.task_history = []

    # =========================================================
    # RESET SESSION
    # =========================================================

    def reset(self):

        self.clear_task()

        self.conversation_history = []

        self.active = True

    # =========================================================
    # END SESSION
    # =========================================================

    def end_session(self):

        self.active = False

        self.task_state = "closed"
