"""Mod table widget factory for the optional Qt UI."""

from __future__ import annotations

from modforge.core.mod_package import ModPackage
from modforge.gui.models import create_mod_table_model
from modforge.gui.qt_compat import load_qt_bindings


def create_mod_table(packages: list[ModPackage] | None = None):
    qt = load_qt_bindings()
    table = qt.QtWidgets.QTableView()
    table.setSortingEnabled(True)
    table.setAlternatingRowColors(True)
    table.setModel(create_mod_table_model(packages or []))
    return table
