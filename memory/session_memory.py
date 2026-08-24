"""
Project : Vyom AI
Version : 1.0
Module  : Session Memory

Purpose:
    Vyom की current conversation और ongoing task की
    working memory रखना।

    यह Long-Term Memory नहीं है।

    यह याद रखता है:
        - अभी user क्या कर रहा है
        - current goal क्या है
        - कौन-सा application active है
        - कौन-सी file active है
        - कौन-सा selection pending है
        - पिछला action क्या था
        - उसका result क्या आया
        - अगला instruction पिछले task की continuation है या नहीं

Architecture:

    Voice / Text
          |
          v
    Autonomous Agent
          |
          v
    Session Memory
          |
          v
    Reasoning / Planning
          |
          v
    Tools / Skills

Security:
    Session Memory को:
        - security बदलने की permission नहीं है
        - permissions बदलने की permission नहीं है
        - generated code execute करने की permission नहीं है
        - core files modify करने की permission नहीं है
"""

from typing import Any, Dict, List, Optional


class SessionMemory:

    def __init__(self):
        # =====================================================
        # SESSION
        # =====================================================

        self.active: bool = True

        # =====================================================
        # CURRENT TASK
        # =====================================================

        self.current_goal: str = ""

        self.last_instruction: str = ""

        self.task_state: str = "idle"

        self.current_step: int = 0

        # =====================================================
        # CURRENT TARGET
        # =====================================================

        self.current_app: Optional[str] = None

        self.current_file: Optional[str] = None

        self.current_target: Optional[str] = None

        # =====================================================
        # LAST ACTION / RESULT
        # =====================================================

        self.last_action: Optional[Dict[str, Any]] = None

        self.last_result: Any = None

        self.last_success: Optional[bool] = None

        # =====================================================
        # SELECTION MEMORY
        # =====================================================

        self.pending_selection: bool = False

        self.selection_target: Optional[str] = None

        self.selection_options: List[Any] = []

        # =====================================================
        # CONFIRMATION
        # =====================================================

        self.awaiting_confirmation: bool = False

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
    # START / CONTINUE TASK
    # =========================================================

    def start_task(
        self,
        instruction: str,
        preserve_context: bool = True
    ):
        """
        नया instruction आने पर current task को start/continue करता है।

        preserve_context=True होने पर पुराना context नहीं मिटता।
        """

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
            role="user",
            text=instruction
        )

    # =========================================================
    # ADD MESSAGE
    # =========================================================

    def add_message(
        self,
        role: str,
        text: str,
        metadata: Optional[
            Dict[str, Any]
        ] = None
    ):
        """
        Conversation का message memory में रखता है।
        """

        self.conversation_history.append(
            {
                "role": str(role),
                "text": str(text),
                "metadata": metadata or {}
            }
        )

        # Memory को अनंत बड़ा होने से रोकना।
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
        """
        Vyom ने अभी कौन-सा action लिया।
        """

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
        """
        Action का result memory में रखता है।
        """

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
    # SELECTION
    # =========================================================

    def set_pending_selection(
        self,
        target: Optional[str] = None,
        options: Optional[List[Any]] = None
    ):
        """
        जब ToolManager multiple results देता है।
        """

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
        """
        Dangerous/permanent action से पहले
        confirmation state।
        """

        self.awaiting_confirmation = True

        self.confirmation_reason = (
            str(reason)
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
    # TASK COMPLETED
    # =========================================================

    def mark_completed(
        self
    ):

        self.task_state = "completed"

    # =========================================================
    # TASK FAILED
    # =========================================================

    def mark_failed(
        self
    ):

        self.task_state = "failed"

    # =========================================================
    # CONTEXT SNAPSHOT
    # =========================================================

    def snapshot(
        self
    ) -> Dict[str, Any]:
        """
        Reasoning Engine को current context देने के लिए
        safe snapshot।
        """

        return {
            "active": self.active,

            "current_goal": (
                self.current_goal
            ),

            "last_instruction": (
                self.last_instruction
            ),

            "task_state": (
                self.task_state
            ),

            "current_step": (
                self.current_step
            ),

            "current_app": (
                self.current_app
            ),

            "current_file": (
                self.current_file
            ),

            "current_target": (
                self.current_target
            ),

            "last_action": (
                self.last_action
            ),

            "last_result": (
                self.last_result
            ),

            "last_success": (
                self.last_success
            ),

            "pending_selection": (
                self.pending_selection
            ),

            "selection_target": (
                self.selection_target
            ),

            "selection_options": (
                list(
                    self.selection_options
                )
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
    # IS CONTINUATION
    # =========================================================

    def is_continuation(
        self
    ) -> bool:
        """
        क्या Vyom के पास पहले से active context है?
        """

        return bool(
            self.current_goal
            or self.current_app
            or self.current_file
            or self.pending_selection
            or self.last_action
        )

    # =========================================================
    # CLEAR CURRENT TASK
    # =========================================================

    def clear_task(
        self
    ):
        """
        Current task साफ करता है,
        लेकिन conversation history को नहीं मिटाता।
        """

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

    def reset(
        self
    ):
        """
        पूरा temporary session reset।
        """

        self.clear_task()

        self.conversation_history = []

        self.active = True

    # =========================================================
    # END SESSION
    # =========================================================

    def end_session(
        self
    ):

        self.active = False

        self.task_state = "closed"
