"""Windows Tcl/Tk bootstrap helpers."""

from __future__ import annotations

import ctypes
import sys
from pathlib import Path

_TCL_PRIMED = False


def prime_tcl_find_executable() -> None:
    """Initialize Tcl's executable path before tkinter creates an interpreter."""

    global _TCL_PRIMED
    if _TCL_PRIMED:
        return
    _TCL_PRIMED = True

    if sys.platform != "win32":
        return

    dll_candidates = [
        Path(sys.base_prefix) / "DLLs" / "tcl86t.dll",
        Path(sys.prefix) / "DLLs" / "tcl86t.dll",
        Path("tcl86t.dll"),
    ]

    tcl = None
    for dll_path in dll_candidates:
        try:
            if dll_path.name != str(dll_path) and not dll_path.exists():
                continue
            tcl = ctypes.WinDLL(str(dll_path))
            break
        except OSError:
            continue

    if tcl is None:
        return

    try:
        tcl.Tcl_FindExecutable.argtypes = [ctypes.c_char_p]
        executable = str(Path(sys.executable).resolve()).replace("\\", "/").encode("utf-8")
        tcl.Tcl_FindExecutable(executable)
    except (AttributeError, OSError, ValueError):
        return
