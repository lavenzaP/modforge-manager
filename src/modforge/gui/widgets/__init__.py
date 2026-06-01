"""Small reusable widgets for the optional Qt UI."""

from modforge.gui.widgets.conflict_panel import format_conflicts
from modforge.gui.widgets.log_viewer import create_log_viewer
from modforge.gui.widgets.mod_table import create_mod_table
from modforge.gui.widgets.project_sidebar import create_project_label, format_project_summary

__all__ = [
    "create_log_viewer",
    "create_mod_table",
    "create_project_label",
    "format_conflicts",
    "format_project_summary",
]
