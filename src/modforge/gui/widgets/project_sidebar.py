"""Project summary widgets for the optional Qt UI."""

from __future__ import annotations

from modforge.core.mod_project import ModProject
from modforge.gui.qt_compat import load_qt_bindings


def format_project_summary(project: ModProject | None) -> str:
    if project is None:
        return "No project loaded."
    return (
        f"{project.name} | game: {project.game_root} | mods: {project.mods_dir} | "
        f"profile: {project.game_profile.id} | user set: {project.active_profile().id}"
    )


def create_project_label(project: ModProject | None = None):
    qt = load_qt_bindings()
    return qt.QtWidgets.QLabel(format_project_summary(project))
