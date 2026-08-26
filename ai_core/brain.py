"""
Project : Vyom AI
Version : 0.3
Module  : Brain

Purpose:
    Lightweight intent logging layer.

Safety:
    Brain only observes/logs the intent. It never executes tools.
"""

from ai_core.logger import log


class Brain:

    def think(self, data):

        if not isinstance(data, dict):
            return "Invalid intent data."

        intent = str(data.get("intent", "unknown"))
        target = str(data.get("target", ""))

        # Keep console logging non-blocking and Unicode-safe as far as
        # the current Windows console permits. A logging failure must
        # NEVER stop the autonomous execution pipeline.
        try:
            log(f"Intent : {intent}")
            try:
                log(f"Target : {target}")
            except (UnicodeEncodeError, UnicodeError):
                safe_target = target.encode("ascii", "backslashreplace").decode("ascii")
                log(f"Target : {safe_target}")
        except Exception:
            pass

        return f"Intent = {intent} | Target = {target}"
