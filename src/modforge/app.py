"""Minimal desktop GUI entry point."""

from __future__ import annotations

from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

from modforge.core.deployer import apply_to_game, apply_to_staging, restore_manifest
from modforge.core.deployment_plan import build_deployment_plan
from modforge.core.game_profile import builtin_profiles
from modforge.core.manifest import InstallManifest
from modforge.core.mod_package import ModPackage, scan_project_mods
from modforge.core.mod_project import ModProject
from modforge.reports.markdown import render_deployment_report
from modforge.tools.checker import ToolCheck, check_tools
from modforge.tools.registry import KNOWN_TOOLS


def main() -> int:
    """Run the current lightweight GUI shell."""

    root = tk.Tk()
    ModForgeApp(root)
    root.mainloop()
    return 0


class ModForgeApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("ModForge Manager")
        self.project: ModProject | None = None
        self.project_path: Path | None = None
        self.packages: list[ModPackage] = []
        self.mod_sort_column = "priority"
        self.mod_sort_reverse = False

        self.status = tk.StringVar(value="Open a modforge.project.json file to begin.")
        self._build()

    def _build(self) -> None:
        self.root.minsize(980, 620)
        frame = ttk.Frame(self.root, padding=12)
        frame.grid(row=0, column=0, sticky="nsew")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(2, weight=1)

        toolbar = ttk.Frame(frame)
        toolbar.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        ttk.Button(toolbar, text="New Project", command=self.new_project).pack(side="left")
        ttk.Button(toolbar, text="Open Project", command=self.open_project).pack(side="left")
        ttk.Button(toolbar, text="Profiles", command=self.manage_profiles).pack(side="left", padx=(8, 0))
        ttk.Button(toolbar, text="Scan", command=self.scan).pack(side="left", padx=(8, 0))
        ttk.Button(toolbar, text="Plan", command=self.plan).pack(side="left", padx=(8, 0))
        ttk.Button(toolbar, text="Save Report", command=self.save_report).pack(side="left", padx=(8, 0))
        ttk.Button(toolbar, text="Apply Staging", command=self.apply_staging).pack(side="left", padx=(8, 0))
        ttk.Button(toolbar, text="Apply Game", command=self.apply_game).pack(side="left", padx=(8, 0))
        ttk.Button(toolbar, text="Restore", command=self.restore).pack(side="left", padx=(8, 0))
        ttk.Button(toolbar, text="Tools", command=self.configure_tools).pack(side="left", padx=(8, 0))

        self.project_info = tk.StringVar(value="No project loaded.")
        ttk.Label(frame, textvariable=self.project_info).grid(row=1, column=0, sticky="ew", pady=(0, 8))

        content = ttk.PanedWindow(frame, orient="vertical")
        content.grid(row=2, column=0, sticky="nsew")

        mod_frame = ttk.Frame(content)
        mod_frame.columnconfigure(0, weight=1)
        mod_frame.rowconfigure(0, weight=1)
        self.mod_table = ttk.Treeview(
            mod_frame,
            columns=("enabled", "priority", "type", "files", "warnings"),
            show="tree headings",
            selectmode="browse",
        )
        self.mod_table.heading("#0", text="Mod", command=lambda: self.set_mod_sort("name"))
        self.mod_table.heading("enabled", text="Enabled", command=lambda: self.set_mod_sort("enabled"))
        self.mod_table.heading("priority", text="Priority", command=lambda: self.set_mod_sort("priority"))
        self.mod_table.heading("type", text="Type", command=lambda: self.set_mod_sort("type"))
        self.mod_table.heading("files", text="Files", command=lambda: self.set_mod_sort("files"))
        self.mod_table.heading("warnings", text="Warnings", command=lambda: self.set_mod_sort("warnings"))
        self.mod_table.column("#0", width=280, anchor="w")
        self.mod_table.column("enabled", width=80, anchor="center")
        self.mod_table.column("priority", width=80, anchor="center")
        self.mod_table.column("type", width=110, anchor="center")
        self.mod_table.column("files", width=80, anchor="center")
        self.mod_table.column("warnings", width=90, anchor="center")
        self.mod_table.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(mod_frame, command=self.mod_table.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.mod_table.configure(yscrollcommand=scrollbar.set)

        mod_controls = ttk.Frame(mod_frame)
        mod_controls.grid(row=1, column=0, sticky="ew", pady=(8, 0))
        ttk.Button(mod_controls, text="Enable", command=lambda: self.set_selected_enabled(True)).pack(side="left")
        ttk.Button(mod_controls, text="Disable", command=lambda: self.set_selected_enabled(False)).pack(
            side="left",
            padx=(8, 0),
        )
        ttk.Button(mod_controls, text="Priority Up", command=lambda: self.move_selected_priority(-1)).pack(
            side="left",
            padx=(8, 0),
        )
        ttk.Button(mod_controls, text="Priority Down", command=lambda: self.move_selected_priority(1)).pack(
            side="left",
            padx=(8, 0),
        )

        output_frame = ttk.Frame(content)
        output_frame.columnconfigure(0, weight=1)
        output_frame.rowconfigure(0, weight=1)
        self.output = tk.Text(output_frame, width=100, height=16, wrap="word")
        self.output.grid(row=0, column=0, sticky="nsew")
        output_scroll = ttk.Scrollbar(output_frame, command=self.output.yview)
        output_scroll.grid(row=0, column=1, sticky="ns")
        self.output.configure(yscrollcommand=output_scroll.set)

        content.add(mod_frame, weight=1)
        content.add(output_frame, weight=1)

        ttk.Label(frame, textvariable=self.status).grid(row=3, column=0, sticky="ew", pady=(8, 0))
        self.progress = ttk.Progressbar(frame, mode="indeterminate")
        self.progress.grid(row=4, column=0, sticky="ew", pady=(4, 0))

    def new_project(self) -> None:
        name = simpledialog.askstring("New ModForge Project", "Project name:")
        if not name:
            return
        game_root = filedialog.askdirectory(title="Select game root")
        if not game_root:
            return
        mods_dir = filedialog.askdirectory(title="Select mods folder")
        if not mods_dir:
            return
        project_file = filedialog.asksaveasfilename(
            title="Save ModForge project",
            initialfile="modforge.project.json",
            defaultextension=".json",
            filetypes=[("ModForge project", "modforge.project.json"), ("JSON", "*.json")],
        )
        if not project_file:
            return
        profile_ids = ", ".join(profile.id for profile in builtin_profiles())
        profile_id = simpledialog.askstring(
            "Game Profile",
            f"Profile id ({profile_ids}):",
            initialvalue="generic-folder",
        )
        if not profile_id:
            return
        project_path = Path(project_file)
        staging_dir = project_path.resolve(strict=False).parent / ".modforge" / "staging"
        try:
            self.project = ModProject.create(name, Path(game_root), Path(mods_dir), staging_dir, profile_id)
        except KeyError as error:
            messagebox.showerror("ModForge Manager", str(error))
            return
        self.project_path = project_path
        self.project.save(project_path)
        self.status.set(f"Created {project_path}")
        self.refresh_project_info()
        self.scan()

    def open_project(self) -> None:
        selected = filedialog.askopenfilename(
            title="Open ModForge project",
            filetypes=[("ModForge project", "modforge.project.json"), ("JSON", "*.json")],
        )
        if not selected:
            return
        self.project_path = Path(selected)
        self.project = ModProject.load(self.project_path)
        self.refresh_project_info()
        self.scan()
        self.status.set(f"Project: {self.project.name}")

    def scan(self) -> None:
        project = self._require_project()
        if project is None:
            return
        self._start_busy("Scanning mods...")
        try:
            self.packages = scan_project_mods(project)
            self.refresh_project_info()
            self.refresh_mod_table()
            self._write(self.scan_summary(project, self.packages))
        except Exception as error:  # pragma: no cover - guarded GUI surface
            self._show_error("Scan failed", error)
            return
        self._stop_busy(f"Scanned {len(self.packages)} mods.")

    def plan(self) -> None:
        project = self._require_project()
        if project is None:
            return
        self._start_busy("Building deployment plan...")
        try:
            packages = self.current_packages()
            plan = build_deployment_plan(project, packages)
            self._write(render_deployment_report(project, plan))
        except Exception as error:  # pragma: no cover - guarded GUI surface
            self._show_error("Plan failed", error)
            return
        self._stop_busy(f"Planned {len(plan.operations)} operations.")

    def save_report(self) -> None:
        project = self._require_project()
        if project is None:
            return
        selected = filedialog.asksaveasfilename(
            title="Save deployment report",
            defaultextension=".md",
            filetypes=[("Markdown", "*.md")],
        )
        if not selected:
            return
        self._start_busy("Writing deployment report...")
        try:
            packages = self.current_packages()
            plan = build_deployment_plan(project, packages)
            Path(selected).write_text(render_deployment_report(project, plan), encoding="utf-8")
        except Exception as error:  # pragma: no cover - guarded GUI surface
            self._show_error("Report failed", error)
            return
        self._stop_busy(f"Wrote {selected}")

    def apply_staging(self) -> None:
        project = self._require_project()
        if project is None:
            return
        if not messagebox.askyesno("Apply staging", "Copy winning files into the staging directory?"):
            return
        self._start_busy("Applying to staging...")
        try:
            packages = self.current_packages()
            plan = build_deployment_plan(project, packages)
            manifest = apply_to_staging(project, plan, packages)
            self._write(self.manifest_summary(manifest.to_dict()))
        except Exception as error:  # pragma: no cover - guarded GUI surface
            self._show_error("Staging apply failed", error)
            return
        self._stop_busy(f"Applied staging manifest {manifest.manifest_id}")

    def apply_game(self) -> None:
        project = self._require_project()
        if project is None:
            return
        confirmed = messagebox.askyesno(
            "Apply to game root",
            "This will write winning files into the game root and create backups. Continue?",
        )
        if not confirmed:
            return
        self._start_busy("Applying to game root...")
        try:
            packages = self.current_packages()
            plan = build_deployment_plan(project, packages)
            manifest = apply_to_game(project, plan, packages)
            self._write(self.manifest_summary(manifest.to_dict()))
        except Exception as error:  # pragma: no cover - guarded GUI surface
            self._show_error("Game apply failed", error)
            return
        self._stop_busy(f"Applied game manifest {manifest.manifest_id}")

    def restore(self) -> None:
        project = self._require_project()
        if project is None:
            return
        manifest_dir = project.staging_dir.parent / "manifests"
        manifest_paths = sorted(manifest_dir.glob("*.json"), key=lambda path: path.stat().st_mtime, reverse=True)
        if not manifest_paths:
            messagebox.showinfo("ModForge Manager", f"No manifests found in {manifest_dir}.")
            return
        dialog = ManifestRestoreDialog(self.root, manifest_paths)
        selection = dialog.show()
        if selection is None:
            return
        manifest_path, selected_paths = selection
        target = "selected files" if selected_paths else "all restorable files"
        if not messagebox.askyesno("Restore manifest", f"Restore {target} from {manifest_path.name}?"):
            return
        self._start_busy("Restoring manifest...")
        try:
            manifest = restore_manifest(manifest_path, selected_paths)
            self._write(self.manifest_summary(manifest.to_dict()))
        except Exception as error:  # pragma: no cover - guarded GUI surface
            self._show_error("Restore failed", error)
            return
        self._stop_busy(f"Restored manifest {manifest.manifest_id}")

    def configure_tools(self) -> None:
        project = self._require_project()
        if project is None:
            return
        dialog = ToolSettingsDialog(self.root, project.external_tools)
        configured_paths = dialog.show()
        if configured_paths is None:
            return
        for tool_id, tool_path in configured_paths.items():
            project.set_tool_path(tool_id, tool_path)
        self.save_project()
        checks = check_tools(project.external_tools)
        self._write(self.tool_checks_summary(checks))
        self.status.set("Saved external tool paths.")

    def manage_profiles(self) -> None:
        project = self._require_project()
        if project is None:
            return
        dialog = UserProfileDialog(self.root, project)
        changed = dialog.show()
        if not changed:
            return
        self.save_project()
        self.refresh_project_info()
        self.scan()
        self.status.set(f"Active user profile: {project.active_profile().name}")

    def set_selected_enabled(self, enabled: bool) -> None:
        project = self._require_project()
        if project is None:
            return
        package = self.selected_package()
        if package is None:
            return
        project.set_mod_enabled(package.id, enabled)
        self.save_project()
        self.scan()

    def move_selected_priority(self, delta: int) -> None:
        project = self._require_project()
        if project is None:
            return
        package = self.selected_package()
        if package is None:
            return
        ordered = [item.id for item in sorted(self.current_packages(), key=lambda item: item.priority)]
        if package.id not in ordered:
            return
        index = ordered.index(package.id)
        target = max(0, min(len(ordered) - 1, index + delta))
        if target == index:
            return
        ordered[index], ordered[target] = ordered[target], ordered[index]
        project.set_priority_order(ordered)
        self.save_project()
        self.scan()

    def refresh_project_info(self) -> None:
        if self.project is None:
            self.project_info.set("No project loaded.")
            return
        self.project_info.set(
            f"{self.project.name} | game: {self.project.game_root} | "
            f"mods: {self.project.mods_dir} | profile: {self.project.game_profile.id} | "
            f"user set: {self.project.active_profile().id} | staging: {self.project.staging_dir}"
        )

    def set_mod_sort(self, column: str) -> None:
        if self.mod_sort_column == column:
            self.mod_sort_reverse = not self.mod_sort_reverse
        else:
            self.mod_sort_column = column
            self.mod_sort_reverse = False
        self.refresh_mod_table()

    def refresh_mod_table(self) -> None:
        self.mod_table.delete(*self.mod_table.get_children())
        for package in self.sorted_packages(self.packages, self.mod_sort_column, self.mod_sort_reverse):
            self.mod_table.insert(
                "",
                "end",
                iid=package.id,
                text=package.name,
                values=(
                    "yes" if package.enabled else "no",
                    package.priority,
                    package.detected_type,
                    len(package.files),
                    len(package.warnings),
                ),
            )

    def current_packages(self) -> list[ModPackage]:
        project = self._require_project()
        if project is None:
            return []
        if not self.packages:
            self.packages = scan_project_mods(project)
        return self.packages

    def selected_package(self) -> ModPackage | None:
        selected = self.mod_table.selection()
        if not selected:
            messagebox.showinfo("ModForge Manager", "Select a mod first.")
            return None
        mod_id = selected[0]
        for package in self.current_packages():
            if package.id == mod_id:
                return package
        return None

    def save_project(self) -> None:
        if self.project and self.project_path:
            self.project.save(self.project_path)

    @staticmethod
    def manifest_summary(manifest: dict[str, object]) -> str:
        return "\n".join(
            [
                f"Manifest: {manifest.get('manifest_id')}",
                f"Target: {manifest.get('target')}",
                f"Copied: {len(manifest.get('copied_files', []))}",
                f"Overwritten: {len(manifest.get('overwritten_files', []))}",
                f"Skipped: {len(manifest.get('skipped_files', []))}",
                f"Backups: {len(manifest.get('backups', []))}",
                "",
                f"Target root: {manifest.get('target_root')}",
                f"Backup dir: {manifest.get('backup_dir')}",
            ]
        )

    @staticmethod
    def tool_checks_summary(checks: list[ToolCheck]) -> str:
        lines = ["External tools:", ""]
        for check in checks:
            state = "OK" if check.exists else "MISSING"
            detail = check.path if check.exists else check.warning
            lines.append(f"{state:7} {check.tool_id} ({check.label})")
            lines.append(f"        {detail}")
        return "\n".join(lines)

    @staticmethod
    def sorted_packages(packages: list[ModPackage], column: str, reverse: bool = False) -> list[ModPackage]:
        def key(package: ModPackage) -> tuple[object, str]:
            fallback = package.name.casefold()
            if column == "name":
                return (fallback, fallback)
            if column == "enabled":
                return (package.enabled, fallback)
            if column == "priority":
                return (package.priority, fallback)
            if column == "type":
                return (package.detected_type, fallback)
            if column == "files":
                return (len(package.files), fallback)
            if column == "warnings":
                return (len(package.warnings), fallback)
            return (package.priority, fallback)

        return sorted(packages, key=key, reverse=reverse)

    @staticmethod
    def scan_summary(project: ModProject, packages: list[ModPackage]) -> str:
        lines = [f"Mods in {project.mods_dir}:", ""]
        for package in ModForgeApp.sorted_packages(packages, "priority"):
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

    @staticmethod
    def manifest_record_rows(manifest: InstallManifest) -> list[tuple[str, str, str, str]]:
        rows = []
        for record in manifest.records:
            if record.status == "skipped":
                continue
            backup = "yes" if record.backup_path else "no"
            rows.append((record.destination_path, record.status, record.source_mod, backup))
        return rows

    def _require_project(self) -> ModProject | None:
        if self.project is None:
            messagebox.showinfo("ModForge Manager", "Open a project file first.")
            return None
        return self.project

    def _write(self, text: str) -> None:
        self.output.delete("1.0", tk.END)
        self.output.insert(tk.END, text)

    def _start_busy(self, label: str) -> None:
        self.status.set(label)
        self.progress.start(8)
        self.root.update_idletasks()

    def _stop_busy(self, label: str) -> None:
        self.progress.stop()
        self.status.set(label)
        self.root.update_idletasks()

    def _show_error(self, title: str, error: Exception) -> None:
        self.progress.stop()
        self.status.set(title)
        messagebox.showerror("ModForge Manager", f"{title}: {error}")


class ToolSettingsDialog:
    def __init__(self, parent: tk.Tk, configured_paths: dict[str, str]) -> None:
        self.parent = parent
        self.result: dict[str, str] | None = None
        self.window = tk.Toplevel(parent)
        self.window.title("External Tools")
        self.window.resizable(True, False)
        self.window.transient(parent)

        frame = ttk.Frame(self.window, padding=12)
        frame.grid(row=0, column=0, sticky="nsew")
        self.window.columnconfigure(0, weight=1)
        frame.columnconfigure(1, weight=1)

        self.variables: dict[str, tk.StringVar] = {}
        for row, (tool_id, label) in enumerate(KNOWN_TOOLS.items()):
            ttk.Label(frame, text=label).grid(row=row, column=0, sticky="w", pady=3)
            variable = tk.StringVar(value=configured_paths.get(tool_id, ""))
            self.variables[tool_id] = variable
            ttk.Entry(frame, textvariable=variable, width=64).grid(row=row, column=1, sticky="ew", padx=(8, 8), pady=3)
            ttk.Button(frame, text="Browse", command=lambda key=tool_id: self.browse(key)).grid(
                row=row,
                column=2,
                sticky="ew",
                pady=3,
            )

        self.check_text = tk.StringVar(value="")
        ttk.Label(frame, textvariable=self.check_text, justify="left").grid(
            row=len(KNOWN_TOOLS),
            column=0,
            columnspan=3,
            sticky="ew",
            pady=(10, 0),
        )

        controls = ttk.Frame(frame)
        controls.grid(row=len(KNOWN_TOOLS) + 1, column=0, columnspan=3, sticky="e", pady=(12, 0))
        ttk.Button(controls, text="Check", command=self.check).pack(side="left")
        ttk.Button(controls, text="Save", command=self.save).pack(side="left", padx=(8, 0))
        ttk.Button(controls, text="Cancel", command=self.cancel).pack(side="left", padx=(8, 0))

        self.window.protocol("WM_DELETE_WINDOW", self.cancel)

    def show(self) -> dict[str, str] | None:
        self.window.grab_set()
        self.window.wait_window()
        return self.result

    def browse(self, tool_id: str) -> None:
        selected = filedialog.askopenfilename(title=f"Select {KNOWN_TOOLS[tool_id]}")
        if selected:
            self.variables[tool_id].set(selected)

    def check(self) -> None:
        checks = check_tools(self.current_paths())
        self.check_text.set(ModForgeApp.tool_checks_summary(checks))

    def save(self) -> None:
        self.result = self.current_paths()
        self.window.destroy()

    def cancel(self) -> None:
        self.result = None
        self.window.destroy()

    def current_paths(self) -> dict[str, str]:
        return {tool_id: variable.get().strip() for tool_id, variable in self.variables.items()}


class ManifestRestoreDialog:
    def __init__(self, parent: tk.Tk, manifest_paths: list[Path]) -> None:
        self.manifest_paths = manifest_paths
        self.current_manifest: InstallManifest | None = None
        self.row_paths: dict[str, str] = {}
        self.result: tuple[Path, list[str] | None] | None = None
        self.window = tk.Toplevel(parent)
        self.window.title("Restore Manifest")
        self.window.geometry("820x480")
        self.window.transient(parent)

        frame = ttk.Frame(self.window, padding=12)
        frame.grid(row=0, column=0, sticky="nsew")
        self.window.columnconfigure(0, weight=1)
        self.window.rowconfigure(0, weight=1)
        frame.columnconfigure(1, weight=1)
        frame.rowconfigure(0, weight=1)

        self.manifest_list = tk.Listbox(frame, height=12, exportselection=False)
        self.manifest_list.grid(row=0, column=0, sticky="ns", padx=(0, 8))
        self.manifest_list.bind("<<ListboxSelect>>", lambda _event: self.load_selected_manifest())

        right = ttk.Frame(frame)
        right.grid(row=0, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)
        right.rowconfigure(1, weight=1)

        self.summary = tk.StringVar(value="")
        ttk.Label(right, textvariable=self.summary).grid(row=0, column=0, sticky="ew", pady=(0, 8))

        self.record_table = ttk.Treeview(
            right,
            columns=("status", "source", "backup"),
            show="tree headings",
            selectmode="extended",
        )
        self.record_table.heading("#0", text="Destination")
        self.record_table.heading("status", text="Status")
        self.record_table.heading("source", text="Source Mod")
        self.record_table.heading("backup", text="Backup")
        self.record_table.column("#0", width=380, anchor="w")
        self.record_table.column("status", width=100, anchor="center")
        self.record_table.column("source", width=160, anchor="w")
        self.record_table.column("backup", width=80, anchor="center")
        self.record_table.grid(row=1, column=0, sticky="nsew")

        controls = ttk.Frame(right)
        controls.grid(row=2, column=0, sticky="e", pady=(10, 0))
        ttk.Button(controls, text="Restore Selected", command=self.restore_selected).pack(side="left")
        ttk.Button(controls, text="Restore All", command=self.restore_all).pack(side="left", padx=(8, 0))
        ttk.Button(controls, text="Cancel", command=self.cancel).pack(side="left", padx=(8, 0))

        self.window.protocol("WM_DELETE_WINDOW", self.cancel)
        for path in self.manifest_paths:
            self.manifest_list.insert(tk.END, path.name)
        self.manifest_list.selection_set(0)
        self.load_selected_manifest()

    def show(self) -> tuple[Path, list[str] | None] | None:
        self.window.grab_set()
        self.window.wait_window()
        return self.result

    def selected_manifest_path(self) -> Path | None:
        selection = self.manifest_list.curselection()
        if not selection:
            return None
        return self.manifest_paths[selection[0]]

    def load_selected_manifest(self) -> None:
        path = self.selected_manifest_path()
        if path is None:
            return
        try:
            manifest = InstallManifest.load(path)
        except (OSError, ValueError) as error:
            messagebox.showerror("ModForge Manager", f"Could not load manifest: {error}")
            return
        self.current_manifest = manifest
        self.summary.set(
            f"{manifest.manifest_id} | target: {manifest.target} | "
            f"copied: {len(manifest.copied_files)} | overwritten: {len(manifest.overwritten_files)}"
        )
        self.record_table.delete(*self.record_table.get_children())
        self.row_paths = {}
        for index, (destination, status, source, backup) in enumerate(ModForgeApp.manifest_record_rows(manifest)):
            item_id = str(index)
            self.row_paths[item_id] = destination
            self.record_table.insert("", "end", iid=item_id, text=destination, values=(status, source, backup))

    def restore_selected(self) -> None:
        path = self.selected_manifest_path()
        if path is None:
            return
        selected_paths = [self.row_paths[item_id] for item_id in self.record_table.selection()]
        if not selected_paths:
            messagebox.showinfo("ModForge Manager", "Select one or more files to restore.")
            return
        self.result = (path, selected_paths)
        self.window.destroy()

    def restore_all(self) -> None:
        path = self.selected_manifest_path()
        if path is None:
            return
        self.result = (path, None)
        self.window.destroy()

    def cancel(self) -> None:
        self.result = None
        self.window.destroy()


class UserProfileDialog:
    def __init__(self, parent: tk.Tk, project: ModProject) -> None:
        self.project = project
        self.changed = False
        self.window = tk.Toplevel(parent)
        self.window.title("User Profiles")
        self.window.resizable(True, False)
        self.window.transient(parent)

        frame = ttk.Frame(self.window, padding=12)
        frame.grid(row=0, column=0, sticky="nsew")
        self.window.columnconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)

        self.listbox = tk.Listbox(frame, height=7, exportselection=False)
        self.listbox.grid(row=0, column=0, columnspan=3, sticky="ew")

        ttk.Label(frame, text="Profile id").grid(row=1, column=0, sticky="w", pady=(10, 0))
        self.id_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.id_var).grid(row=2, column=0, columnspan=3, sticky="ew")

        ttk.Label(frame, text="Display name").grid(row=3, column=0, sticky="w", pady=(8, 0))
        self.name_var = tk.StringVar()
        ttk.Entry(frame, textvariable=self.name_var).grid(row=4, column=0, columnspan=3, sticky="ew")

        controls = ttk.Frame(frame)
        controls.grid(row=5, column=0, columnspan=3, sticky="ew", pady=(12, 0))
        ttk.Button(controls, text="Switch", command=self.switch).pack(side="left")
        ttk.Button(controls, text="Create", command=lambda: self.create(copy_active=False)).pack(side="left", padx=(8, 0))
        ttk.Button(controls, text="Clone Active", command=lambda: self.create(copy_active=True)).pack(
            side="left",
            padx=(8, 0),
        )
        ttk.Button(controls, text="Delete", command=self.delete).pack(side="left", padx=(8, 0))
        ttk.Button(controls, text="Close", command=self.close).pack(side="right")

        self.window.protocol("WM_DELETE_WINDOW", self.close)
        self.refresh()

    def show(self) -> bool:
        self.window.grab_set()
        self.window.wait_window()
        return self.changed

    def refresh(self) -> None:
        self.listbox.delete(0, tk.END)
        active_index = 0
        for index, profile in enumerate(self.project.user_profiles):
            marker = "*" if profile.id == self.project.active_user_profile else " "
            self.listbox.insert(tk.END, f"{marker} {profile.id} - {profile.name}")
            if profile.id == self.project.active_user_profile:
                active_index = index
        self.listbox.selection_set(active_index)

    def selected_profile_id(self) -> str | None:
        selected = self.listbox.curselection()
        if not selected:
            return None
        return self.project.user_profiles[selected[0]].id

    def switch(self) -> None:
        profile_id = self.selected_profile_id()
        if profile_id is None:
            return
        self.project.switch_user_profile(profile_id)
        self.changed = True
        self.refresh()

    def create(self, copy_active: bool) -> None:
        profile_id = self.id_var.get().strip()
        if not profile_id:
            messagebox.showinfo("ModForge Manager", "Enter a profile id first.")
            return
        copy_from = self.project.active_user_profile if copy_active else None
        try:
            profile = self.project.create_user_profile(profile_id, self.name_var.get().strip() or None, copy_from)
        except ValueError as error:
            messagebox.showerror("ModForge Manager", str(error))
            return
        self.project.switch_user_profile(profile.id)
        self.changed = True
        self.id_var.set("")
        self.name_var.set("")
        self.refresh()

    def delete(self) -> None:
        profile_id = self.selected_profile_id()
        if profile_id is None:
            return
        try:
            self.project.delete_user_profile(profile_id)
        except ValueError as error:
            messagebox.showerror("ModForge Manager", str(error))
            return
        self.changed = True
        self.refresh()

    def close(self) -> None:
        self.window.destroy()


if __name__ == "__main__":
    raise SystemExit(main())
