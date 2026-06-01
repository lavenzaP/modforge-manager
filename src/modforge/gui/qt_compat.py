"""Lazy PySide6 loading helpers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class PySide6Unavailable(RuntimeError):
    """Raised when the optional Qt GUI is requested without PySide6."""


@dataclass(frozen=True, slots=True)
class QtBindings:
    QtCore: Any
    QtGui: Any
    QtWidgets: Any


_BINDINGS: QtBindings | None = None
_IMPORT_ERROR: ImportError | None = None


def install_message(error: ImportError | None = None) -> str:
    details = f" ({error})" if error else ""
    return (
        "PySide6 is not available"
        f"{details}. Install the optional GUI extra with `pip install -e .[gui]`, "
        "or use the standard-library tkinter UI with `modforge-gui`."
    )


def load_qt_bindings() -> QtBindings:
    global _BINDINGS, _IMPORT_ERROR
    if _BINDINGS is not None:
        return _BINDINGS
    try:
        from PySide6 import QtCore, QtGui, QtWidgets
    except ImportError as error:
        _IMPORT_ERROR = error
        raise PySide6Unavailable(install_message(error)) from error
    _IMPORT_ERROR = None
    _BINDINGS = QtBindings(QtCore=QtCore, QtGui=QtGui, QtWidgets=QtWidgets)
    return _BINDINGS


def pyside6_status() -> tuple[bool, str]:
    try:
        load_qt_bindings()
    except PySide6Unavailable as error:
        return False, str(error)
    return True, "PySide6 is available."
