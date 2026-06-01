"""Minimal desktop GUI entry point."""

from __future__ import annotations

from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from modforge.core.deployment_plan import build_deployment_plan
from modforge.core.mod_package import scan_mods
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

        self.status = tk.StringVar(value="Open a modforge.project.json file to begin.")
        self._build()

    def _build(self) -> None:
        frame = ttk.Frame(self.root, padding=12)
        frame.grid(row=0, column=0, sticky="nsew")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)
        frame.rowconfigure(1, weight=1)

        toolbar = ttk.Frame(frame)
        toolbar.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        ttk.Button(toolbar, text="Open Project", command=self.open_project).pack(side="left")
        ttk.Button(toolbar, text="Scan", command=self.scan).pack(side="left", padx=(8, 0))
        ttk.Button(toolbar, text="Plan", command=self.plan).pack(side="left", padx=(8, 0))
        ttk.Button(toolbar, text="Save Report", command=self.save_report).pack(side="left", padx=(8, 0))

        self.output = tk.Text(frame, width=100, height=32, wrap="word")
        self.output.grid(row=1, column=0, sticky="nsew")
        ttk.Label(frame, textvariable=self.status).grid(row=2, column=0, sticky="ew", pady=(8, 0))

    def open_project(self) -> None:
        selected = filedialog.askopenfilename(
            title="Open ModForge project",
            filetypes=[("ModForge project", "modforge.project.json"), ("JSON", "*.json")],
        )
        if not selected:
            return
        self.project_path = Path(selected)
        self.project = ModProject.load(self.project_path)
        self._write(f"Opened {self.project.name}\n{self.project_path}")
        self.status.set(f"Project: {self.project.name}")

    def scan(self) -> None:
        project = self._require_project()
        if project is None:
            return
        packages = scan_mods(project.mods_dir, project.active_profile())
        lines = [f"Mods in {project.mods_dir}:", ""]
        for package in packages:
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
        packages = scan_mods(project.mods_dir, project.active_profile())
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
        packages = scan_mods(project.mods_dir, project.active_profile())
        plan = build_deployment_plan(project, packages)
        Path(selected).write_text(render_deployment_report(project, plan), encoding="utf-8")
        self.status.set(f"Wrote {selected}")

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
