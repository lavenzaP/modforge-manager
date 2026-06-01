"""Log/output widget factory for the optional Qt UI."""

from __future__ import annotations

from modforge.gui.qt_compat import load_qt_bindings


def create_log_viewer(initial_text: str = ""):
    qt = load_qt_bindings()
    viewer = qt.QtWidgets.QPlainTextEdit()
    viewer.setReadOnly(True)
    viewer.setPlainText(initial_text)
    return viewer
