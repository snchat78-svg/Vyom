"""
Project : Vyom AI
Version : 1.0
Module  : World State Model

Purpose:
    Provide a lightweight snapshot of the computer/task state to
    reasoning and planning layers.

This module observes; it does not execute or modify applications.
It is intentionally dependency-free for Vyom's low-resource target.
"""

import os
import subprocess
import time
from typing import Any, Dict, Optional


class WorldStateModel:

    def __init__(self, max_processes: int = 30):
        self.max_processes = max(5, int(max_processes))
        self.last_snapshot: Optional[Dict[str, Any]] = None

    def _running_processes(self):
        if os.name != "nt":
            return []

        try:
            result = subprocess.run(
                ["tasklist", "/FO", "CSV", "/NH"],
                capture_output=True,
                text=True,
                timeout=3,
            )
            processes = []
            for line in result.stdout.splitlines():
                line = line.strip()
                if not line or line.startswith("INFO:"):
                    continue
                first = line.split('","', 1)[0].replace('"', "").strip()
                if first:
                    processes.append(first)
            return processes[:self.max_processes]
        except Exception:
            return []

    def snapshot(self, session_context: Optional[Dict[str, Any]] = None):
        ctx = session_context if isinstance(session_context, dict) else {}

        state = {
            "timestamp": time.time(),
            "platform": os.name,
            "cwd": os.getcwd(),
            "current_app": ctx.get("current_app"),
            "current_file": ctx.get("current_file"),
            "current_target": ctx.get("current_target"),
            "task_state": ctx.get("task_state"),
            "last_success": ctx.get("last_success"),
            "pending_selection": ctx.get("pending_selection", False),
            "awaiting_confirmation": ctx.get("awaiting_confirmation", False),
            "running_processes": self._running_processes(),
        }
        self.last_snapshot = state
        return state
