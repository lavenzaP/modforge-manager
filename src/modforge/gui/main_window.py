"""Optional PySide6 desktop UI."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from modforge.core.deployer import apply_to_game, apply_to_staging
from modforge.core.deployment_plan import build_deployment_plan
from modforge.core.manifest import InstallManifest
from modforge.core.mod_package import ModPackage, scan_project_mods
from modforge.core.mod_project import ModProject
from modforge.gui.models import create_mod_table_model
from modforge.gui.qt_compat import PySide6Unavailable, load_qt_bindings, pyside6_status
from modforge.gui.widgets import create_log_viewer, create_mod_table, create_project_label
from modforge.gui.widgets import format_project_summary
from modforge.reports.markdown import render_deployment_report
from modforge.tools.checker import ToolCheck, check_tools


class MainWindow:
    """Thin PySide6 wrapper around the same core workflow as the tkinter UI."""

    def __init__(self, project_path: Path | None = None) -> None:
        self.qt = load_qt_bindings()
        self.project: ModProject | None = None
        self.project_path: Path | None = None
        self.packages: list[ModPackage] = []

        self.window = self.qt.QtWidgets.QMainWindow()
        self.window.setWindowTitle("ModForge Manager Qt")
        self.window.resize(1120, 720)
        self._build()
        if project_path is not None:
            self.load_project(project_path)

    def show(self) -> None:
        self.window.show()

    def _build(self) -> None:
        widgets = self.qt.QtWidgets
        core = self.qt.QtCore
        gui = self.qt.QtGui

        toolbar = widgets.QToolBar("Workflow")
        self.window.addToolBar(toolbar)
        self._add_action(toolbar, gui, "Open Project", self.open_project)
        self._add_action(toolbar, gui, "Scan", self.scan)
        self._add_action(toolbar, gui, "Plan", self.plan)
        self._add_action(toolbar, gui, "Save Report", self.save_report)
        self._add_action(toolbar, gui, "Apply Staging", self.apply_staging)
        self._add_action(toolbar, gui, "Apply Game", self.apply_game)
        self._add_action(toolbar, gui, "Tools Check", self.check_tools)

        central = widgets.QWidget()
        layout = widgets.QVBoxLayout(central)
        self.info_label = create_project_label()
        layout.addWidget(self.info_label)

        splitter = widgets.QSplitter(core.Qt.Orientation.Vertical)
        self.table = create_mod_table()
        splitter.addWidget(self.table)

        self.output = create_log_viewer()
        splitter.addWidget(self.output)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)
        layout.addWidget(splitter)

        self.window.setCentralWidget(central)
        self.window.statusBar().showMessage("Open a modforge.project.json file to begin.")

    def _add_action(self, toolbar, gui, label: str, callback) -> None:
        action = gui.QAction(label, self.window)
        action.triggered.connect(lambda _checked=False, selected=callback: selected())
        toolbar.addAction(action)

    def open_project(self) -> None:
        selected, _filter = self.qt.QtWidgets.QFileDialog.getOpenFileName(
            self.window,
            "Open ModForge project",
            "",
            "ModForge project (modforge.project.json);;JSON (*.json)",
        )
        if selected:
            self.load_project(Path(selected))

    def load_project(self, project_path: Path) -> None:
        try:
            self.project = ModProject.load(project_path)
        except (AttributeError, OSError, KeyError, TypeError, ValueError) as error:
            self._show_error("Project load failed", error)
            return
        self.project_path = project_path
        self.packages = []
        self.refresh_project_info()
        self.scan()

    def scan(self) -> None:
        project = self._require_project()
        if project is None:
            return
        self._set_status("Scanning mods...")
        try:
            self.packages = scan_project_mods(project)
            self.table.setModel(create_mod_table_model(self.packages))
            self.output.setPlainText(format_scan_summary(project, self.packages))
        except Exception as error:  # pragma: no cover - guarded GUI surface
            self._show_error("Scan failed", error)
            return
        self.refresh_project_info()
        self._set_status(f"Scanned {len(self.packages)} mods.")

    def plan(self) -> None:
        project = self._require_project()
        if project is None:
            return
        self._set_status("Building deployment plan...")
        try:
            packages = self.current_packages()
            plan = build_deployment_plan(project, packages)
            self.output.setPlainText(render_deployment_report(project, plan))
        except Exception as error:  # pragma: no cover - guarded GUI surface
            self._show_error("Plan failed", error)
            return
        self._set_status(f"Planned {len(plan.operations)} operations.")

    def save_report(self) -> None:
        project = self._require_project()
        if project is None:
            return
        selected, _filter = self.qt.QtWidgets.QFileDialog.getSaveFileName(
            self.window,
            "Save deployment report",
            "",
            "Markdown (*.md)",
        )
        if not selected:
            return
        try:
            packages = self.current_packages()
            plan = build_deployment_plan(project, packages)
            Path(selected).write_text(render_deployment_report(project, plan), encoding="utf-8")
        except Exception as error:  # pragma: no cover - guarded GUI surface
            self._show_error("Report failed", error)
            return
        self._set_status(f"Wrote {selected}")

    def apply_staging(self) -> None:
        project = self._require_project()
        if project is None:
            return
        if not self._confirm("Apply staging", "Copy winning files into the staging directory?"):
            return
        try:
            packages = self.current_packages()
            plan = build_deployment_plan(project, packages)
            manifest = apply_to_staging(project, plan, packages)
            self.output.setPlainText(format_manifest_summary(manifest))
        except Exception as error:  # pragma: no cover - guarded GUI surface
            self._show_error("Staging apply failed", error)
            return
        self._set_status(f"Applied staging manifest {manifest.manifest_id}.")

    def apply_game(self) -> None:
        project = self._require_project()
        if project is None:
            return
        confirmed = self._confirm(
            "Apply to game root",
            "This will write winning files into the game root and create backups. Continue?",
        )
        if not confirmed:
            return
        try:
            packages = self.current_packages()
            plan = build_deployment_plan(project, packages)
            manifest = apply_to_game(project, plan, packages)
            self.output.setPlainText(format_manifest_summary(manifest))
        except Exception as error:  # pragma: no cover - guarded GUI surface
            self._show_error("Game apply failed", error)
            return
        self._set_status(f"Applied game manifest {manifest.manifest_id}.")

    def check_tools(self) -> None:
        project = self._require_project()
        if project is None:
            return
        self.output.setPlainText(format_tool_checks(check_tools(project.external_tools)))
        self._set_status("Checked external tool configuration.")

    def current_packages(self) -> list[ModPackage]:
        project = self._require_project()
        if project is None:
            return []
        if not self.packages:
            self.packages = scan_project_mods(project)
        return self.packages

    def refresh_project_info(self) -> None:
        if self.project is None:
            self.info_label.setText(format_project_summary(None))
            return
        self.info_label.setText(format_project_summary(self.project))

    def _require_project(self) -> ModProject | None:
        if self.project is None:
            self.qt.QtWidgets.QMessageBox.information(
                self.window,
                "ModForge Manager",
                "Open a project file first.",
            )
            return None
        return self.project

    def _confirm(self, title: str, message: str) -> bool:
        buttons = (
            self.qt.QtWidgets.QMessageBox.StandardButton.Yes
            | self.qt.QtWidgets.QMessageBox.StandardButton.No
        )
        answer = self.qt.QtWidgets.QMessageBox.question(self.window, title, message, buttons)
        return answer == self.qt.QtWidgets.QMessageBox.StandardButton.Yes

    def _show_error(self, title: str, error: Exception) -> None:
        self._set_status(title)
        self.qt.QtWidgets.QMessageBox.critical(self.window, "ModForge Manager", f"{title}: {error}")

    def _set_status(self, message: str) -> None:
        self.window.statusBar().showMessage(message)


def format_scan_summary(project: ModProject, packages: list[ModPackage]) -> str:
    lines = [f"Mods in {project.mods_dir}:", ""]
    for package in sorted(packages, key=lambda item: (item.priority, item.name.casefold())):
        state = "on" if package.enabled else "off"
        lines.append(
            f"{package.priority:03d} {state:3} {package.name} "
            f"({package.detected_type}, {len(package.files)} files)"
        )
        if package.extracted_path:
            lines.append(f"    extracted: {package.extracted_path}")
        for warning in package.warnings:
            lines.append(f"    warning: {warning}")
    return "\n".join(lines)


def format_tool_checks(checks: list[ToolCheck]) -> str:
    lines = ["External tools:", ""]
    for check in checks:
        state = "OK" if check.exists else "MISSING"
        detail = check.path if check.exists else check.warning
        lines.append(f"{state:7} {check.tool_id} ({check.label})")
        lines.append(f"        {detail}")
    return "\n".join(lines)


def format_manifest_summary(manifest: InstallManifest) -> str:
    payload = manifest.to_dict()
    return "\n".join(
        [
            f"Manifest: {payload.get('manifest_id')}",
            f"Target: {payload.get('target')}",
            f"Copied: {len(payload.get('copied_files', []))}",
            f"Overwritten: {len(payload.get('overwritten_files', []))}",
            f"Skipped: {len(payload.get('skipped_files', []))}",
            f"Backups: {len(payload.get('backups', []))}",
            "",
            f"Target root: {payload.get('target_root')}",
            f"Backup dir: {payload.get('backup_dir')}",
        ]
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="modforge-gui-qt")
    parser.add_argument("project_file", nargs="?", type=Path)
    parser.add_argument(
        "--check-dependency",
        action="store_true",
        help="Check whether the optional PySide6 dependency is available.",
    )
    args = parser.parse_args(argv)

    if args.check_dependency:
        available, message = pyside6_status()
        print(message, file=sys.stdout if available else sys.stderr)
        return 0 if available else 1

    try:
        qt = load_qt_bindings()
    except PySide6Unavailable as error:
        print(str(error), file=sys.stderr)
        return 1

    app = qt.QtWidgets.QApplication.instance() or qt.QtWidgets.QApplication(sys.argv[:1])
    window = MainWindow(args.project_file)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
