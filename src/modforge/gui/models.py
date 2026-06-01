"""Shared model helpers for the optional Qt UI."""

from __future__ import annotations

from dataclasses import dataclass

from modforge.core.mod_package import ModPackage
from modforge.gui.qt_compat import load_qt_bindings


MOD_TABLE_HEADERS = ["Mod", "Enabled", "Priority", "Type", "Files", "Warnings"]


@dataclass(frozen=True, slots=True)
class ModRow:
    mod_id: str
    name: str
    enabled: bool
    priority: int
    package_type: str
    file_count: int
    warning_count: int

    @classmethod
    def from_package(cls, package: ModPackage) -> "ModRow":
        return cls(
            mod_id=package.id,
            name=package.name,
            enabled=package.enabled,
            priority=package.priority,
            package_type=package.detected_type,
            file_count=len(package.files),
            warning_count=len(package.warnings),
        )

    def display_values(self) -> list[str]:
        return [
            self.name,
            "yes" if self.enabled else "no",
            str(self.priority),
            self.package_type,
            str(self.file_count),
            str(self.warning_count),
        ]


def build_mod_rows(packages: list[ModPackage]) -> list[ModRow]:
    return [ModRow.from_package(package) for package in sorted(packages, key=_package_sort_key)]


def create_mod_table_model(packages: list[ModPackage]):
    qt = load_qt_bindings()
    model = qt.QtGui.QStandardItemModel(0, len(MOD_TABLE_HEADERS))
    model.setHorizontalHeaderLabels(MOD_TABLE_HEADERS)
    for row in build_mod_rows(packages):
        items = [_read_only_item(qt, value) for value in row.display_values()]
        items[0].setData(row.mod_id, _user_role(qt))
        model.appendRow(items)
    return model


def _package_sort_key(package: ModPackage) -> tuple[int, str]:
    return (package.priority, package.name.casefold())


def _read_only_item(qt, value: str):
    item = qt.QtGui.QStandardItem(value)
    item.setEditable(False)
    return item


def _user_role(qt):
    return qt.QtCore.Qt.ItemDataRole.UserRole
