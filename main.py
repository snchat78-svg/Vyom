"""Vyom AI root launcher.

The CI build uses ai_core/main.py directly. This file keeps
`python main.py` usable from the repository root as well.
"""

from ai_core.main import main


if __name__ == "__main__":
    main()
