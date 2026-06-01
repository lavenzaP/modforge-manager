"""Source-tree import helper for local commands.

When Python starts from the repository root, this lets stdlib commands such as
`python -m unittest discover -s tests` import the `src/` package without first
installing the project.
"""

from __future__ import annotations

import sys
from pathlib import Path

SRC = Path(__file__).resolve().parent / "src"
if SRC.exists() and str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))
