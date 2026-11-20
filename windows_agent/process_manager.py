"""
Project : Vyom AI
Version : 0.9
Module  : Process Manager

Safety:
    - Match an exact executable image name, never a substring.
    - Ask Windows to close a single unambiguous PID gracefully.
    - Verify whether that PID exited.
    - Never force-kill every process sharing an image name.
"""

import csv
import io
import os
import subprocess


class ProcessManager:

    @staticmethod
    def _normalize_executable_name(value):
        name = str(value or "").strip().strip('"').replace("/", "\\")
        if not name:
            return ""
        name = os.path.basename(name).lower()
        if not name.endswith(".exe"):
            name += ".exe"
        return name

    @staticmethod
    def _running_processes():
        result = subprocess.run(
            ["tasklist", "/FO", "CSV", "/NH"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            detail = str(result.stderr or result.stdout or "tasklist failed").strip()
            raise RuntimeError(detail[:240])

        processes = []
        reader = csv.reader(io.StringIO(str(result.stdout or "")))
        for row in reader:
            if len(row) < 2:
                continue
            image_name = str(row[0] or "").strip()
            try:
                pid = int(str(row[1]).strip())
            except (TypeError, ValueError):
                continue
            if image_name and pid > 0:
                processes.append({"image_name": image_name, "pid": pid})
        return processes

    def close_app(self, process_name):
        requested = self._normalize_executable_name(process_name)
        if not requested:
            return "Please specify an application to close."

        try:
            processes = self._running_processes()
        except Exception as error:
            return "Error reading running processes: %s" % type(error).__name__

        # Exact basename equality only. "calc.exe" must not match
        # "Calculator.exe" or any other name containing the same substring.
        matches = [
            item for item in processes
            if str(item.get("image_name") or "").strip().lower() == requested
        ]

        if not matches:
            return (
                "No exact running process was found for '%s'. "
                "The active-window close route may still work for this application."
            ) % requested

        if len(matches) != 1:
            pids = ", ".join(str(item["pid"]) for item in matches[:8])
            return (
                "Multiple '%s' instances are running (PIDs: %s). "
                "Please select the window to close; no process was terminated."
            ) % (requested, pids)

        pid = matches[0]["pid"]
        try:
            close_result = subprocess.run(
                ["taskkill", "/PID", str(pid), "/T"],
                capture_output=True,
                text=True,
                timeout=10,
            )
        except Exception as error:
            return "Graceful close request failed: %s" % type(error).__name__

        if close_result.returncode != 0:
            detail = str(close_result.stderr or close_result.stdout or "").strip()
            return "Windows did not accept a graceful close request for PID %s. %s" % (
                pid, detail[:180]
            )

        try:
            remaining = self._running_processes()
        except Exception:
            return (
                "A graceful close request was sent to PID %s, but Vyom could not "
                "verify that it exited. No force termination was attempted."
            ) % pid

        if any(item.get("pid") == pid for item in remaining):
            return (
                "A graceful close request was sent to '%s' (PID %s), but it is "
                "still running. Vyom did not force-terminate it."
            ) % (requested, pid)

        return "Closed '%s' (PID %s); process exit was verified." % (requested, pid)
