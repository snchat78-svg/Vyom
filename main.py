"""Vyom AI root launcher.

The CI build uses ai_core/main.py directly. This file keeps
`python main.py` usable from the repository root as well.
"""

from ai_core.main import *  # noqa: F401,F403
