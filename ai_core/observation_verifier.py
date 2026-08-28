"""
Project : Vyom AI
Version : 1.0
Module  : Observation Verifier

Purpose:
    Verify whether an executed Windows task actually produced
    the expected computer state.

Design:
    - Does not execute arbitrary code.
    - Does not modify security settings.
    - Uses read-only Windows observations.
    - Works without requiring psutil.
    - Keeps verification separate from ToolManager.
"""

import os
import re
import subprocess
import time
from typing import Any, Dict, Optional


class ObservationVerifier:

    def __init__(
        self,
        wait_seconds: float = 1.0
    ):
        self.wait_seconds = max(
            0.0,
            float(wait_seconds)
        )

        # Common application -> process aliases.
        #
        # This is only a verification hint.
        # It is NOT an application registry.
        self.process_aliases = {
            "notepad": [
                "notepad.exe",
                "notepad"
            ],
            "calculator": [
                "calculator.exe",
                "calculatorapp.exe",
                "calculator"
            ],
            "calc": [
                "calculator.exe",
                "calculatorapp.exe",
                "calculator"
            ],
            "chrome": [
                "chrome.exe",
                "chrome"
            ],
            "google chrome": [
                "chrome.exe",
                "chrome"
            ],
            "edge": [
                "msedge.exe",
                "msedge"
            ],
            "microsoft edge": [
                "msedge.exe",
                "msedge"
            ],
            "firefox": [
                "firefox.exe",
                "firefox"
            ],
            "word": [
                "winword.exe",
                "winword"
            ],
            "microsoft word": [
                "winword.exe",
                "winword"
            ],
            "excel": [
                "excel.exe",
                "excel"
            ],
            "microsoft excel": [
                "excel.exe",
                "excel"
            ],
            "powerpoint": [
                "powerpnt.exe",
                "powerpnt"
            ],
            "microsoft powerpoint": [
                "powerpnt.exe",
                "powerpnt"
            ],
            "paint": [
                "mspaint.exe",
                "mspaint"
            ],
            "cmd": [
                "cmd.exe",
                "cmd"
            ],
            "command prompt": [
                "cmd.exe",
                "cmd"
            ],
            "powershell": [
                "powershell.exe",
                "powershell"
            ]
        }

    # =========================================================
    # PUBLIC VERIFY
    # =========================================================

    def verify(
        self,
        intent: Optional[Dict[str, Any]],
        result: Any = None
    ) -> Dict[str, Any]:

        intent = (
            intent
            if isinstance(intent, dict)
            else {}
        )

        intent_name = str(
            intent.get(
                "intent",
                "unknown"
            )
        ).strip().lower()

        target = str(
            intent.get(
                "target",
                ""
            ) or ""
        ).strip()

        # -----------------------------------------------------
        # Basic execution failure
        # -----------------------------------------------------

        if self._result_failed(result):
            return {
                "verified": False,
                "state": "execution_failed",
                "reason": "Tool execution reported failure.",
                "intent": intent_name,
                "target": target
            }

        # -----------------------------------------------------
        # OPEN APPLICATION
        # -----------------------------------------------------

        if intent_name == "open":
            return self.verify_open(
                target
            )

        # -----------------------------------------------------
        # OPEN FILE
        # -----------------------------------------------------

        if intent_name in (
            "open_file",
            "search_and_open_file"
        ):
            return self.verify_file(
                target
            )

        # -----------------------------------------------------
        # SEARCH FILE
        #
        # Search may legitimately return a list rather than
        # opening anything.
        # -----------------------------------------------------

        if intent_name == "search_file":
            return {
                "verified": True,
                "state": "search_completed",
                "reason": (
                    "Search operation returned a result."
                ),
                "intent": intent_name,
                "target": target
            }

        # -----------------------------------------------------
        # CLOSE APPLICATION
        # -----------------------------------------------------

        if intent_name == "close_app":
            return self.verify_closed(
                target
            )

        # -----------------------------------------------------
        # Unknown operation
        #
        # Do not falsely claim success.
        # -----------------------------------------------------

        return {
            "verified": False,
            "state": "unverified",
            "reason": (
                "No observation strategy exists "
                "for this intent yet."
            ),
            "intent": intent_name,
            "target": target
        }

    # =========================================================
    # OPEN VERIFICATION
    # =========================================================

    def verify_open(
        self,
        target: str
    ) -> Dict[str, Any]:

        target = str(
            target or ""
        ).strip()

        if not target:
            return {
                "verified": False,
                "state": "missing_target",
                "reason": "No open target was supplied."
            }

        # -----------------------------------------------------
        # Existing file/folder/path
        # -----------------------------------------------------

        if self._looks_like_path(target):
            if os.path.exists(target):
                return {
                    "verified": True,
                    "state": "path_exists",
                    "reason": (
                        "The requested file/folder exists."
                    ),
                    "target": target
                }

        # -----------------------------------------------------
        # Application process
        # -----------------------------------------------------

        aliases = self._get_process_aliases(
            target
        )

        if aliases:
            time.sleep(
                self.wait_seconds
            )

            running = self._find_running_process(
                aliases
            )

            if running:
                return {
                    "verified": True,
                    "state": "application_running",
                    "reason": (
                        "The target application process "
                        "was observed."
                    ),
                    "target": target,
                    "process": running
                }

            return {
                "verified": False,
                "state": "application_not_observed",
                "reason": (
                    "The launcher reported success, "
                    "but the expected process was not observed."
                ),
                "target": target,
                "expected_processes": aliases
            }

        # -----------------------------------------------------
        # Unknown application
        #
        # We must NOT claim verified success.
        # -----------------------------------------------------

        return {
            "verified": False,
            "state": "unknown_target",
            "reason": (
                "Target has no safe process observation "
                "mapping yet."
            ),
            "target": target
        }

    # =========================================================
    # FILE VERIFICATION
    # =========================================================

    def verify_file(
        self,
        target: str
    ) -> Dict[str, Any]:

        target = str(
            target or ""
        ).strip()

        if os.path.exists(target):
            return {
                "verified": True,
                "state": "file_exists",
                "reason": (
                    "The requested file/folder exists."
                ),
                "target": target
            }

        return {
            "verified": False,
            "state": "file_not_found",
            "reason": (
                "The requested file/folder "
                "could not be observed."
            ),
            "target": target
        }

    # =========================================================
    # CLOSE VERIFICATION
    # =========================================================

    def verify_closed(
        self,
        target: str
    ) -> Dict[str, Any]:

        target = str(
            target or ""
        ).strip()

        aliases = self._get_process_aliases(
            target
        )

        if not aliases:
            return {
                "verified": False,
                "state": "unknown_target",
                "reason": (
                    "Cannot safely verify closed state "
                    "for this application yet."
                ),
                "target": target
            }

        time.sleep(
            self.wait_seconds
        )

        running = self._find_running_process(
            aliases
        )

        if running:
            return {
                "verified": False,
                "state": "still_running",
                "reason": (
                    "The application process is still running."
                ),
                "target": target,
                "process": running
            }

        return {
            "verified": True,
            "state": "application_closed",
            "reason": (
                "The expected application process "
                "is no longer running."
            ),
            "target": target
        }

    # =========================================================
    # PROCESS LOOKUP
    # =========================================================

    def _find_running_process(
        self,
        process_names
    ) -> Optional[str]:

        names = {
            str(name).strip().lower()
            for name in process_names
            if name
        }

        if not names:
            return None

        # -----------------------------------------------------
        # Preferred: tasklist
        #
        # Available on normal Windows installations.
        # -----------------------------------------------------

        try:
            completed = subprocess.run(
                [
                    "tasklist",
                    "/FO",
                    "CSV",
                    "/NH"
                ],
                capture_output=True,
                text=True,
                timeout=5,
                creationflags=(
                    getattr(
                        subprocess,
                        "CREATE_NO_WINDOW",
                        0
                    )
                )
            )

            if completed.returncode == 0:
                output = (
                    completed.stdout
                    or ""
                )

                for line in output.splitlines():

                    lowered = line.lower()

                    for name in names:

                        if (
                            f'"{name}"'
                            in lowered
                        ):
                            return name

                        # Some Windows versions may return
                        # slightly different formatting.
                        if (
                            name in lowered
                            and name.endswith(
                                ".exe"
                            )
                        ):
                            return name

        except Exception:
            pass

        return None

    # =========================================================
    # PROCESS ALIASES
    # =========================================================

    def _get_process_aliases(
        self,
        target: str
    ):

        normalized = (
            str(target or "")
            .strip()
            .lower()
        )

        if normalized in self.process_aliases:
            return self.process_aliases[
                normalized
            ]

        # Remove common punctuation.
        simplified = re.sub(
            r"[^a-z0-9 ]+",
            " ",
            normalized
        )

        simplified = " ".join(
            simplified.split()
        )

        if simplified in self.process_aliases:
            return self.process_aliases[
                simplified
            ]

        # Executable target.
        basename = os.path.basename(
            normalized
        )

        if basename.endswith(
            ".exe"
        ):
            return [
                basename
            ]

        return []

    # =========================================================
    # PATH DETECTION
    # =========================================================

    def _looks_like_path(
        self,
        target: str
    ) -> bool:

        target = str(
            target or ""
        ).strip()

        if not target:
            return False

        if os.path.exists(target):
            return True

        if (
            len(target) >= 3
            and target[1:3] == ":\\"
        ):
            return True

        if target.startswith(
            "\\\\"
        ):
            return True

        if (
            "/" in target
            or "\\" in target
        ):
            return True

        return False

    # =========================================================
    # RESULT FAILURE
    # =========================================================

    def _result_failed(
        self,
        result
    ) -> bool:

        if result is None:
            return True

        if isinstance(
            result,
            dict
        ):
            if (
                "success" in result
                and
                not result.get(
                    "success"
                )
            ):
                return True

            if "error" in result:
                return True

            return False

        if isinstance(
            result,
            bool
        ):
            return not result

        text = str(
            result
        ).strip().lower()

        if not text:
            return True

        failure_phrases = (
            "error",
            "failed",
            "failure",
            "could not",
            "not found",
            "unable to",
            "exception",
            "no tool available"
        )

        return any(
            phrase in text
            for phrase in failure_phrases
        )
