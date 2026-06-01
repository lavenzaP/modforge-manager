"""Minimal desktop GUI entry point."""

from __future__ import annotations

from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

from modforge.core.deployer import apply_to_game, apply_to_staging, restore_manifest
from modforge.core.deployment_plan import build_deployment_plan
from modforge.core.mod_package import ModPackage, scan_mods
from modforge.core.mod_project import ModProject
from modforge.reports.markdown import render_deployment_report


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
        ttk.Button(toolbar, text="Scan", command=self.scan).pack(side="left", padx=(8, 0))
        ttk.Button(toolbar, text="Plan", command=self.plan).pack(side="left", padx=(8, 0))
        ttk.Button(toolbar, text="Save Report", command=self.save_report).pack(side="left", padx=(8, 0))
        ttk.Button(toolbar, text="Apply Staging", command=self.apply_staging).pack(side="left", padx=(8, 0))
        ttk.Button(toolbar, text="Apply Game", command=self.apply_game).pack(side="left", padx=(8, 0))
        ttk.Button(toolbar, text="Restore", command=self.restore).pack(side="left", padx=(8, 0))

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
        self.mod_table.heading("#0", text="Mod")
        self.mod_table.heading("enabled", text="Enabled")
        self.mod_table.heading("priority", text="Priority")
        self.mod_table.heading("type", text="Type")
        self.mod_table.heading("files", text="Files")
        self.mod_table.heading("warnings", text="Warnings")
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
        project_path = Path(project_file)
        staging_dir = project_path.resolve(strict=False).parent / ".modforge" / "staging"
        self.project = ModProject.create(name, Path(game_root), Path(mods_dir), staging_dir)
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
        self.packages = scan_mods(project.mods_dir, project.active_profile())
        self.refresh_project_info()
        self.refresh_mod_table()
        lines = [f"Mods in {project.mods_dir}:", ""]
        for package in self.packages:
            state = "on" if package.enabled else "off"
            lines.append(
                f"{package.priority:03d} {state:3} {package.name} "
                f"({package.detected_type}, {len(package.files)} files)"
            )
        self._write("\n".join(lines))

    def plan(self) -> None:
        project = self._require_project()
        if project is None:
            return
        packages = self.current_packages()
        plan = build_deployment_plan(project, packages)
        self._write(render_deployment_report(project, plan))

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
        packages = self.current_packages()
        plan = build_deployment_plan(project, packages)
        Path(selected).write_text(render_deployment_report(project, plan), encoding="utf-8")
        self.status.set(f"Wrote {selected}")

    def apply_staging(self) -> None:
        project = self._require_project()
        if project is None:
            return
        if not messagebox.askyesno("Apply staging", "Copy winning files into the staging directory?"):
            return
        packages = self.current_packages()
        plan = build_deployment_plan(project, packages)
        manifest = apply_to_staging(project, plan, packages)
        self._write(self.manifest_summary(manifest.to_dict()))
        self.status.set(f"Applied staging manifest {manifest.manifest_id}")

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
        packages = self.current_packages()
        plan = build_deployment_plan(project, packages)
        manifest = apply_to_game(project, plan, packages)
        self._write(self.manifest_summary(manifest.to_dict()))
        self.status.set(f"Applied game manifest {manifest.manifest_id}")

    def restore(self) -> None:
        selected = filedialog.askopenfilename(
            title="Select ModForge manifest",
            filetypes=[("Manifest JSON", "*.json"), ("All files", "*.*")],
        )
        if not selected:
            return
        if not messagebox.askyesno("Restore manifest", "Restore files using this manifest?"):
            return
        manifest = restore_manifest(Path(selected))
        self._write(self.manifest_summary(manifest.to_dict()))
        self.status.set(f"Restored manifest {manifest.manifest_id}")

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
            f"mods: {self.project.mods_dir} | staging: {self.project.staging_dir}"
        )

    def refresh_mod_table(self) -> None:
        self.mod_table.delete(*self.mod_table.get_children())
        for package in sorted(self.packages, key=lambda item: item.priority):
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
            self.packages = scan_mods(project.mods_dir, project.active_profile())
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

    def _require_project(self) -> ModProject | None:
        if self.project is None:
            messagebox.showinfo("ModForge Manager", "Open a project file first.")
            return None
        return self.project

    def _write(self, text: str) -> None:
        self.output.delete("1.0", tk.END)
        self.output.insert(tk.END, text)


if __name__ == "__main__":
    raise SystemExit(main())
