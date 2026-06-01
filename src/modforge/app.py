"""Minimal desktop GUI entry point."""

from __future__ import annotations

from pathlib import Path
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

from modforge.core.deployer import apply_to_game, apply_to_staging, preview_restore_manifest, restore_manifest
from modforge.core.deployment_plan import build_deployment_plan, summarize_deployment_plan
from modforge.core.game_profile import builtin_profile, builtin_profiles
from modforge.core.manifest import InstallManifest
from modforge.core.manifest_browser import list_manifest_summaries
from modforge.core.mod_package import ModPackage, scan_project_mods
from modforge.core.mod_project import ModProject
from modforge.core.project_portability import audit_project
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
        self.root.geometry("1440x860")
        self.root.minsize(1180, 720)
        self.root.configure(bg="#0f151d")
        self._configure_style()

        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        self.project_info = tk.StringVar(value="No project loaded.")
        self.project_name_var = tk.StringVar(value="Project:  -")
        self.project_path_var = tk.StringVar(value="Open a project to begin.")
        self.profile_var = tk.StringVar(value="generic-folder")
        self.mod_set_var = tk.StringVar(value="Default")
        self.search_var = tk.StringVar(value="")
        self.search_var.trace_add("write", lambda *_args: self.refresh_mod_table())
        self.kpi_vars = {
            "total": (tk.StringVar(value="0"), tk.StringVar(value="Scanned: 0")),
            "enabled": (tk.StringVar(value="0"), tk.StringVar(value="0.0%")),
            "conflicts": (tk.StringVar(value="0"), tk.StringVar(value="No plan yet")),
            "warnings": (tk.StringVar(value="0"), tk.StringVar(value="All clear")),
            "plan": (tk.StringVar(value="Ready"), tk.StringVar(value="No plan yet")),
            "set": (tk.StringVar(value="Default"), tk.StringVar(value="0 enabled")),
        }
        self.table_rows: dict[str, str] = {}

        shell = ttk.Frame(self.root, style="App.TFrame")
        shell.grid(row=0, column=0, sticky="nsew")
        shell.columnconfigure(0, weight=1)
        shell.rowconfigure(1, weight=1)

        header = ttk.Frame(shell, style="Header.TFrame", padding=(14, 10))
        header.grid(row=0, column=0, sticky="ew")
        header.columnconfigure(2, weight=1)

        logo = tk.Canvas(header, width=40, height=40, bg="#0c1118", bd=0, highlightthickness=0)
        logo.create_rectangle(6, 6, 34, 34, outline="#3f8cff", width=2)
        logo.create_line(10, 26, 10, 12, 20, 22, 30, 12, 30, 26, fill="#61a6ff", width=2)
        logo.grid(row=0, column=0, rowspan=2, sticky="w", padx=(0, 12))
        ttk.Label(header, text="ModForge Manager", style="Title.TLabel").grid(row=0, column=1, sticky="w")
        ttk.Label(header, text="v0.1.0 MVP RC", style="Muted.TLabel").grid(row=1, column=1, sticky="w")

        project_block = ttk.Frame(header, style="Header.TFrame")
        project_block.grid(row=0, column=2, rowspan=2, sticky="w", padx=(26, 0))
        ttk.Label(project_block, textvariable=self.project_name_var, style="HeaderText.TLabel").grid(
            row=0,
            column=0,
            sticky="w",
        )
        ttk.Label(project_block, textvariable=self.project_path_var, style="Muted.TLabel").grid(
            row=1,
            column=0,
            sticky="w",
        )

        profile_block = ttk.Frame(header, style="Header.TFrame")
        profile_block.grid(row=0, column=3, rowspan=2, sticky="e", padx=(20, 20))
        ttk.Label(profile_block, text="Game Profile:", style="HeaderText.TLabel").grid(
            row=0,
            column=0,
            sticky="e",
            padx=(0, 8),
        )
        self.profile_box = ttk.Combobox(
            profile_block,
            textvariable=self.profile_var,
            values=[profile.id for profile in builtin_profiles()],
            width=22,
            state="readonly",
            style="Dark.TCombobox",
        )
        self.profile_box.grid(row=0, column=1, sticky="e")
        self.profile_box.bind("<<ComboboxSelected>>", lambda _event: self.change_game_profile())

        ttk.Label(header, text="Dry-run by default", style="SafeBadge.TLabel", padding=(12, 8)).grid(
            row=0,
            column=4,
            rowspan=2,
            sticky="e",
        )

        body = ttk.Frame(shell, style="App.TFrame")
        body.grid(row=1, column=0, sticky="nsew")
        body.columnconfigure(1, weight=1)
        body.rowconfigure(0, weight=1)

        sidebar = ttk.Frame(body, style="Sidebar.TFrame", padding=(8, 14))
        sidebar.grid(row=0, column=0, sticky="ns")
        sidebar.grid_propagate(False)
        sidebar.configure(width=196)
        for index, label in enumerate(
            [
                "Dashboard",
                "Project",
                "Mods",
                "Mod Sets",
                "Conflicts",
                "Plan",
                "Reports",
                "Apply & Restore",
                "Manifests",
                "Translation Extract",
                "Tools",
                "Audit / Doctor",
            ]
        ):
            style = "SidebarSelected.TButton" if label == "Mods" else "Sidebar.TButton"
            ttk.Button(sidebar, text=label, style=style).grid(row=index, column=0, sticky="ew", pady=2)

        sidebar.rowconfigure(12, weight=1)
        modset_card = ttk.Frame(sidebar, style="Panel.TFrame", padding=10)
        modset_card.grid(row=13, column=0, sticky="sew", pady=(12, 0))
        ttk.Label(modset_card, text="Active Mod Set", style="Muted.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(modset_card, textvariable=self.mod_set_var, style="CardValue.TLabel").grid(
            row=1,
            column=0,
            sticky="w",
            pady=(4, 8),
        )
        ttk.Button(modset_card, text="Manage Mod Sets", command=self.manage_profiles, style="Dark.TButton").grid(
            row=2,
            column=0,
            sticky="ew",
        )

        main = ttk.Frame(body, style="App.TFrame", padding=(12, 10))
        main.grid(row=0, column=1, sticky="nsew")
        main.columnconfigure(0, weight=1)
        main.rowconfigure(2, weight=1)

        actions = ttk.Frame(main, style="App.TFrame")
        actions.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        for label, command, style in [
            ("Open Project", self.open_project, "Dark.TButton"),
            ("Scan Mods", self.scan, "Dark.TButton"),
            ("Plan", self.plan, "Dark.TButton"),
            ("Save Report", self.save_report, "Dark.TButton"),
            ("Apply Staging", self.apply_staging, "Blue.TButton"),
            ("Apply Game", self.apply_game, "Red.TButton"),
            ("Restore", self.restore, "Purple.TButton"),
            ("Tools Check", self.configure_tools, "Dark.TButton"),
            ("Health", self.health, "Dark.TButton"),
        ]:
            ttk.Button(actions, text=label, command=command, style=style).pack(side="left", padx=(0, 8))

        stats = ttk.Frame(main, style="App.TFrame")
        stats.grid(row=1, column=0, sticky="ew", pady=(0, 10))
        for index, (title, key, accent) in enumerate(
            [
                ("Total Mods", "total", "#6b7280"),
                ("Enabled", "enabled", "#22c55e"),
                ("Conflicts", "conflicts", "#ef4444"),
                ("Scan Warnings", "warnings", "#f59e0b"),
                ("Last Plan", "plan", "#22c55e"),
                ("Active Mod Set", "set", "#3b82f6"),
            ]
        ):
            card = self._metric_card(stats, title, key, accent)
            card.grid(row=0, column=index, sticky="ew", padx=(0 if index == 0 else 4, 4))
            stats.columnconfigure(index, weight=1)

        work = ttk.Frame(main, style="App.TFrame")
        work.grid(row=2, column=0, sticky="nsew")
        work.columnconfigure(0, weight=1)
        work.rowconfigure(0, weight=1)
        work.rowconfigure(1, weight=0)

        center = ttk.Frame(work, style="App.TFrame")
        center.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        center.columnconfigure(0, weight=1)
        center.rowconfigure(0, weight=1)

        self.tabs = ttk.Notebook(center, style="Dark.TNotebook")
        self.tabs.grid(row=0, column=0, sticky="nsew")

        mods_tab = ttk.Frame(self.tabs, style="Panel.TFrame", padding=8)
        mods_tab.columnconfigure(0, weight=1)
        mods_tab.rowconfigure(1, weight=1)
        self.tabs.add(mods_tab, text="Mods")

        table_toolbar = ttk.Frame(mods_tab, style="Panel.TFrame")
        table_toolbar.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        search = ttk.Entry(table_toolbar, textvariable=self.search_var, width=28, style="Dark.TEntry")
        search.pack(side="left", padx=(0, 8))
        search.insert(0, "")
        for label, command in [
            ("Enable", lambda: self.set_selected_enabled(True)),
            ("Disable", lambda: self.set_selected_enabled(False)),
            ("Move Up", lambda: self.move_selected_priority(-1)),
            ("Move Down", lambda: self.move_selected_priority(1)),
            ("Rescan", self.scan),
        ]:
            ttk.Button(table_toolbar, text=label, command=command, style="Dark.TButton").pack(side="left", padx=(0, 6))

        table_frame = ttk.Frame(mods_tab, style="Panel.TFrame")
        table_frame.grid(row=1, column=0, sticky="nsew")
        table_frame.columnconfigure(0, weight=1)
        table_frame.rowconfigure(0, weight=1)
        self.mod_table = ttk.Treeview(
            table_frame,
            columns=("enabled", "priority", "name", "type", "source", "status", "warnings", "conflicts"),
            show="headings",
            selectmode="browse",
            style="Mod.Treeview",
        )
        self.mod_table.heading("enabled", text="Enabled", command=lambda: self.set_mod_sort("enabled"))
        self.mod_table.heading("priority", text="Priority", command=lambda: self.set_mod_sort("priority"))
        self.mod_table.heading("name", text="Mod Name", command=lambda: self.set_mod_sort("name"))
        self.mod_table.heading("type", text="Type", command=lambda: self.set_mod_sort("type"))
        self.mod_table.heading("source", text="Source")
        self.mod_table.heading("status", text="Status")
        self.mod_table.heading("warnings", text="Warnings", command=lambda: self.set_mod_sort("warnings"))
        self.mod_table.heading("conflicts", text="Destination Conflicts")
        self.mod_table.column("enabled", width=74, anchor="center", stretch=False)
        self.mod_table.column("priority", width=78, anchor="center", stretch=False)
        self.mod_table.column("name", width=210, anchor="w")
        self.mod_table.column("type", width=120, anchor="center")
        self.mod_table.column("source", width=170, anchor="w")
        self.mod_table.column("status", width=84, anchor="center", stretch=False)
        self.mod_table.column("warnings", width=90, anchor="center", stretch=False)
        self.mod_table.column("conflicts", width=130, anchor="center", stretch=False)
        self.mod_table.grid(row=0, column=0, sticky="nsew")
        self.mod_table.bind("<<TreeviewSelect>>", lambda _event: self.refresh_selected_detail())
        scrollbar = ttk.Scrollbar(table_frame, command=self.mod_table.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.mod_table.configure(yscrollcommand=scrollbar.set)
        self.mod_table.tag_configure("disabled", foreground="#7b8492")
        self.mod_table.tag_configure("warning", foreground="#fbbf24")
        self.mod_table.tag_configure("conflict", foreground="#fca5a5")

        self.mod_count_label = ttk.Label(mods_tab, text="0 mods", style="Muted.TLabel")
        self.mod_count_label.grid(row=2, column=0, sticky="w", pady=(8, 0))

        conflicts_tab = ttk.Frame(self.tabs, style="Panel.TFrame", padding=8)
        conflicts_tab.columnconfigure(0, weight=1)
        conflicts_tab.rowconfigure(0, weight=1)
        self.conflict_output = self._text_widget(conflicts_tab, height=12)
        self.conflict_output.grid(row=0, column=0, sticky="nsew")
        self.tabs.add(conflicts_tab, text="Conflicts")

        plan_tab = ttk.Frame(self.tabs, style="Panel.TFrame", padding=8)
        plan_tab.columnconfigure(0, weight=1)
        plan_tab.rowconfigure(0, weight=1)
        self.plan_output = self._text_widget(plan_tab, height=12)
        self.plan_output.grid(row=0, column=0, sticky="nsew")
        self.tabs.add(plan_tab, text="Plan Preview")

        restore_tab = ttk.Frame(self.tabs, style="Panel.TFrame", padding=8)
        restore_tab.columnconfigure(0, weight=1)
        restore_tab.rowconfigure(0, weight=1)
        self.restore_output = self._text_widget(restore_tab, height=12)
        self.restore_output.grid(row=0, column=0, sticky="nsew")
        self.tabs.add(restore_tab, text="Restore Preview")

        log_panel = ttk.Frame(work, style="Panel.TFrame", padding=(8, 6))
        log_panel.grid(row=1, column=0, sticky="ew", padx=(0, 10), pady=(10, 0))
        log_panel.columnconfigure(0, weight=1)
        ttk.Label(log_panel, text="Live Log", style="TabTitle.TLabel").grid(row=0, column=0, sticky="w")
        self.output = self._text_widget(log_panel, height=7)
        self.output.grid(row=1, column=0, sticky="ew", pady=(6, 0))

        details = ttk.Frame(work, style="App.TFrame")
        details.grid(row=0, column=1, rowspan=2, sticky="nsew")
        details.configure(width=330)
        details.grid_propagate(False)
        details.columnconfigure(0, weight=1)

        self.detail_title = tk.StringVar(value="No mod selected")
        detail_card = ttk.Frame(details, style="Panel.TFrame", padding=12)
        detail_card.grid(row=0, column=0, sticky="ew")
        ttk.Label(detail_card, textvariable=self.detail_title, style="PanelTitle.TLabel").grid(
            row=0,
            column=0,
            sticky="w",
        )
        self.detail_text = self._text_widget(detail_card, height=12)
        self.detail_text.grid(row=1, column=0, sticky="ew", pady=(8, 0))

        conflict_card = ttk.Frame(details, style="Panel.TFrame", padding=12)
        conflict_card.grid(row=1, column=0, sticky="ew", pady=(10, 0))
        ttk.Label(conflict_card, text="Conflict Summary", style="PanelTitle.TLabel").grid(row=0, column=0, sticky="w")
        self.side_conflict_text = self._text_widget(conflict_card, height=8)
        self.side_conflict_text.grid(row=1, column=0, sticky="ew", pady=(8, 0))
        ttk.Button(
            conflict_card,
            text="View Conflicts in Tab",
            command=lambda: self.tabs.select(conflicts_tab),
            style="Dark.TButton",
        ).grid(
            row=2,
            column=0,
            sticky="ew",
            pady=(8, 0),
        )

        apply_card = ttk.Frame(details, style="Panel.TFrame", padding=12)
        apply_card.grid(row=2, column=0, sticky="ew", pady=(10, 0))
        ttk.Label(apply_card, text="Apply / Manifest Status", style="PanelTitle.TLabel").grid(
            row=0,
            column=0,
            sticky="w",
        )
        self.apply_status_text = self._text_widget(apply_card, height=7)
        self.apply_status_text.grid(row=1, column=0, sticky="ew", pady=(8, 0))

        footer = ttk.Frame(shell, style="Header.TFrame", padding=(14, 8))
        footer.grid(row=2, column=0, sticky="ew")
        footer.columnconfigure(0, weight=1)
        ttk.Label(footer, textvariable=self.status, style="Footer.TLabel").grid(row=0, column=0, sticky="w")
        self.progress = ttk.Progressbar(footer, mode="indeterminate", length=180)
        self.progress.grid(row=0, column=1, sticky="e")
        self.refresh_project_info()

    def _configure_style(self) -> None:
        style = ttk.Style(self.root)
        if "clam" in style.theme_names():
            style.theme_use("clam")

        style.configure("App.TFrame", background="#0f151d")
        style.configure("Header.TFrame", background="#0b1017")
        style.configure("Sidebar.TFrame", background="#101720")
        style.configure("Panel.TFrame", background="#151c25", relief="solid", borderwidth=1)
        style.configure("Title.TLabel", background="#0b1017", foreground="#f8fafc", font=("Segoe UI", 13, "bold"))
        style.configure("HeaderText.TLabel", background="#0b1017", foreground="#f8fafc", font=("Segoe UI", 10, "bold"))
        style.configure("Muted.TLabel", background="#0b1017", foreground="#9aa4b2", font=("Segoe UI", 9))
        style.configure("Footer.TLabel", background="#0b1017", foreground="#cbd5e1", font=("Segoe UI", 9))
        style.configure("SafeBadge.TLabel", background="#0d2417", foreground="#59d878", font=("Segoe UI", 9, "bold"))
        style.configure("PanelTitle.TLabel", background="#151c25", foreground="#f8fafc", font=("Segoe UI", 11, "bold"))
        style.configure("CardTitle.TLabel", background="#151c25", foreground="#cbd5e1", font=("Segoe UI", 9))
        style.configure("CardValue.TLabel", background="#151c25", foreground="#f8fafc", font=("Segoe UI", 18, "bold"))
        style.configure("CardSub.TLabel", background="#151c25", foreground="#9aa4b2", font=("Segoe UI", 8))
        style.configure("TabTitle.TLabel", background="#151c25", foreground="#58a6ff", font=("Segoe UI", 9, "bold"))

        for name, foreground, background in [
            ("Dark.TButton", "#e5e7eb", "#1d2630"),
            ("Blue.TButton", "#eff6ff", "#1e5799"),
            ("Red.TButton", "#fff7ed", "#a83b2c"),
            ("Purple.TButton", "#f5f3ff", "#33204f"),
            ("Sidebar.TButton", "#d7dde7", "#101720"),
            ("SidebarSelected.TButton", "#dbeafe", "#163e73"),
        ]:
            style.configure(name, foreground=foreground, background=background, borderwidth=1, padding=(12, 8))
            style.map(name, background=[("active", "#263241")])

        style.configure("Dark.TEntry", fieldbackground="#101720", foreground="#e5e7eb", insertcolor="#e5e7eb")
        style.configure("Dark.TCombobox", fieldbackground="#1d2630", foreground="#f8fafc", arrowcolor="#cbd5e1")
        style.configure("Dark.TNotebook", background="#151c25", borderwidth=0)
        style.configure("Dark.TNotebook.Tab", background="#151c25", foreground="#cbd5e1", padding=(14, 8))
        style.map("Dark.TNotebook.Tab", background=[("selected", "#111827")], foreground=[("selected", "#58a6ff")])
        style.configure(
            "Mod.Treeview",
            background="#111820",
            fieldbackground="#111820",
            foreground="#dbe4ef",
            rowheight=34,
            borderwidth=0,
            font=("Segoe UI", 9),
        )
        style.configure(
            "Mod.Treeview.Heading",
            background="#151c25",
            foreground="#cbd5e1",
            relief="flat",
            font=("Segoe UI", 9, "bold"),
        )
        style.map("Mod.Treeview", background=[("selected", "#1f4f89")], foreground=[("selected", "#ffffff")])

    def _metric_card(self, parent: ttk.Frame, title: str, key: str, accent: str) -> ttk.Frame:
        value, subtitle = self.kpi_vars[key]
        card = ttk.Frame(parent, style="Panel.TFrame", padding=12)
        card.columnconfigure(0, weight=1)
        stripe = tk.Frame(card, bg=accent, width=3)
        stripe.grid(row=0, column=0, rowspan=3, sticky="nsw", padx=(0, 10))
        ttk.Label(card, text=title, style="CardTitle.TLabel").grid(row=0, column=1, sticky="w")
        ttk.Label(card, textvariable=value, style="CardValue.TLabel").grid(row=1, column=1, sticky="w", pady=(4, 0))
        ttk.Label(card, textvariable=subtitle, style="CardSub.TLabel").grid(row=2, column=1, sticky="w", pady=(4, 0))
        return card

    def _text_widget(self, parent: ttk.Frame, height: int) -> tk.Text:
        return tk.Text(
            parent,
            height=height,
            wrap="word",
            bg="#101720",
            fg="#dbe4ef",
            insertbackground="#dbe4ef",
            relief="flat",
            padx=8,
            pady=8,
            font=("Consolas", 9),
        )

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
            self._write_to(self.plan_output, "Run Plan to preview deployment operations.")
            self.refresh_selected_detail()
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
            report = render_deployment_report(project, plan)
            self._write(report)
            self._write_to(self.plan_output, report)
            self._write_to(self.conflict_output, self.conflict_summary(plan))
            self._write_to(self.side_conflict_text, self.compact_conflict_summary(plan))
            self._write_to(self.apply_status_text, self.apply_status_summary(plan))
            self.refresh_project_info()
            self.refresh_mod_table()
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
            summary = self.manifest_summary(manifest.to_dict())
            self._write(summary)
            self._write_to(self.apply_status_text, summary)
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
            summary = self.manifest_summary(manifest.to_dict())
            self._write(summary)
            self._write_to(self.apply_status_text, summary)
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
        try:
            preview = preview_restore_manifest(manifest_path, selected_paths)
        except Exception as error:  # pragma: no cover - guarded GUI surface
            self._show_error("Restore preview failed", error)
            return
        preview_summary = self.restore_preview_summary(preview.to_dict())
        if not preview.to_dict().get("can_restore"):
            messagebox.showerror("ModForge Manager", f"Restore is blocked:\n\n{preview_summary}")
            self._write(preview_summary)
            self._write_to(self.restore_output, preview_summary)
            return
        target = "selected files" if selected_paths else "all restorable files"
        if not messagebox.askyesno(
            "Restore manifest",
            f"Restore {target} from {manifest_path.name}?\n\n{preview_summary}",
        ):
            return
        self._start_busy("Restoring manifest...")
        try:
            manifest = restore_manifest(manifest_path, selected_paths)
            summary = self.manifest_summary(manifest.to_dict())
            self._write(summary)
            self._write_to(self.restore_output, summary)
        except Exception as error:  # pragma: no cover - guarded GUI surface
            self._show_error("Restore failed", error)
            return
        self._stop_busy(f"Restored manifest {manifest.manifest_id}")

    def health(self) -> None:
        project = self._require_project()
        if project is None:
            return
        audit = audit_project(project)
        manifests = list_manifest_summaries(project)
        summary = self.project_health_summary(audit.to_dict(), [manifest.to_dict() for manifest in manifests])
        self._write(summary)
        self._write_to(self.apply_status_text, summary)
        status = "Project has issues." if audit.has_errors or audit.has_warnings else "Project health is OK."
        self.status.set(status)

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
        summary = self.tool_checks_summary(checks)
        self._write(summary)
        self._write_to(self.apply_status_text, summary)
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

    def change_game_profile(self) -> None:
        project = self.project
        if project is None:
            return
        profile_id = self.profile_var.get().strip()
        try:
            project.game_profile = builtin_profile(profile_id)
        except KeyError as error:
            messagebox.showerror("ModForge Manager", str(error))
            return
        self.save_project()
        self.scan()
        self.status.set(f"Game profile: {profile_id}")

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
            self.project_name_var.set("Project:  -")
            self.project_path_var.set("Open a project to begin.")
            self.profile_var.set("generic-folder")
            self.mod_set_var.set("Default")
            self._set_kpis(0, 0, 0, 0, "Ready", "No plan yet")
            return
        profile = self.project.active_profile()
        total = len(self.packages)
        enabled = sum(1 for package in self.packages if package.enabled)
        warnings = sum(len(package.warnings) for package in self.packages)
        conflicts = 0
        plan_state = "Ready" if self.packages else "No scan"
        plan_subtitle = "Scan complete" if self.packages else "No plan yet"
        if self.packages:
            try:
                plan = build_deployment_plan(self.project, self.packages)
                conflicts = len(plan.conflicts)
                summary = summarize_deployment_plan(plan)
                plan_state = str(summary["risk_level"]).title()
                plan_subtitle = f"{summary['operations']} ops, {conflicts} conflicts"
            except Exception:
                plan_state = "Blocked"
                plan_subtitle = "Plan unavailable"

        self.project_info.set(
            f"{self.project.name} | game: {self.project.game_root} | mods: {self.project.mods_dir} | "
            f"profile: {self.project.game_profile.id} | user set: {profile.id} | staging: {self.project.staging_dir}"
        )
        self.project_name_var.set(f"Project:  {self.project.name}")
        self.project_path_var.set(str(self.project_path or self.project.game_root))
        self.profile_var.set(self.project.game_profile.id)
        self.mod_set_var.set(profile.name)
        self._set_kpis(total, enabled, conflicts, warnings, plan_state, plan_subtitle)

    def _set_kpis(
        self,
        total: int,
        enabled: int,
        conflicts: int,
        warnings: int,
        plan_state: str,
        plan_subtitle: str,
    ) -> None:
        enabled_ratio = (enabled / total * 100) if total else 0
        self.kpi_vars["total"][0].set(str(total))
        self.kpi_vars["total"][1].set(f"Scanned: {total}")
        self.kpi_vars["enabled"][0].set(str(enabled))
        self.kpi_vars["enabled"][1].set(f"{enabled_ratio:.1f}%")
        self.kpi_vars["conflicts"][0].set(str(conflicts))
        self.kpi_vars["conflicts"][1].set("Review needed" if conflicts else "No conflicts")
        self.kpi_vars["warnings"][0].set(str(warnings))
        self.kpi_vars["warnings"][1].set("Review recommended" if warnings else "All clear")
        self.kpi_vars["plan"][0].set(plan_state)
        self.kpi_vars["plan"][1].set(plan_subtitle)
        self.kpi_vars["set"][0].set(self.mod_set_var.get())
        self.kpi_vars["set"][1].set(f"{enabled} enabled")

    def set_mod_sort(self, column: str) -> None:
        if self.mod_sort_column == column:
            self.mod_sort_reverse = not self.mod_sort_reverse
        else:
            self.mod_sort_column = column
            self.mod_sort_reverse = False
        self.refresh_mod_table()

    def refresh_mod_table(self) -> None:
        self.mod_table.delete(*self.mod_table.get_children())
        self.table_rows = {}
        query = self.search_var.get().strip().casefold() if hasattr(self, "search_var") else ""
        conflict_counts = self._conflict_counts_by_mod()
        shown = 0
        sorted_packages = self.sorted_packages(
            self.packages,
            self.mod_sort_column,
            self.mod_sort_reverse,
        )
        for index, package in enumerate(sorted_packages):
            if query and query not in package.name.casefold() and query not in package.detected_type.casefold():
                continue
            row_id = f"{package.id}:{index}"
            self.table_rows[row_id] = package.id
            conflicts = conflict_counts.get(package.name, 0)
            tags = []
            if not package.enabled:
                tags.append("disabled")
            if package.warnings:
                tags.append("warning")
            if conflicts:
                tags.append("conflict")
            self.mod_table.insert(
                "",
                "end",
                iid=row_id,
                values=(
                    "On" if package.enabled else "Off",
                    package.priority,
                    package.name,
                    package.detected_type,
                    package.path.name,
                    "OK" if package.enabled else "Disabled",
                    len(package.warnings) if package.warnings else "-",
                    conflicts if conflicts else "-",
                ),
                tags=tuple(tags),
            )
            shown += 1
        enabled = sum(1 for package in self.packages if package.enabled)
        self.mod_count_label.configure(text=f"{shown} mods shown ({enabled} enabled)")
        self.refresh_selected_detail()

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
        mod_id = self.table_rows.get(selected[0], selected[0])
        for package in self.current_packages():
            if package.id == mod_id:
                return package
        return None

    def refresh_selected_detail(self) -> None:
        package = self.selected_package_or_none()
        if package is None:
            self.detail_title.set("No mod selected")
            self._write_to(self.detail_text, "Select a mod to inspect its files, warnings, source, and status.")
            return
        warnings = "\n".join(f"- {warning}" for warning in package.warnings) or "-"
        extracted = str(package.extracted_path) if package.extracted_path else "N/A"
        detail = "\n".join(
            [
                f"Name: {package.name}",
                f"Enabled: {'yes' if package.enabled else 'no'}",
                f"Priority: {package.priority}",
                f"Type: {package.detected_type}",
                f"Source: {package.path}",
                f"Files: {len(package.files)}",
                f"Extracted: {extracted}",
                "",
                "Warnings:",
                warnings,
            ]
        )
        self.detail_title.set(package.name)
        self._write_to(self.detail_text, detail)

    def selected_package_or_none(self) -> ModPackage | None:
        selected = self.mod_table.selection()
        if not selected:
            return None
        mod_id = self.table_rows.get(selected[0], selected[0])
        for package in self.current_packages():
            if package.id == mod_id:
                return package
        return None

    def _conflict_counts_by_mod(self) -> dict[str, int]:
        project = self.project
        if project is None or not self.packages:
            return {}
        try:
            plan = build_deployment_plan(project, self.packages)
        except Exception:
            return {}
        counts: dict[str, int] = {}
        for conflict in plan.conflicts:
            for mod_name in conflict.mods:
                counts[mod_name] = counts.get(mod_name, 0) + 1
        return counts

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
    def restore_preview_summary(preview: dict[str, object]) -> str:
        records = preview.get("records", [])
        warnings = preview.get("warnings", [])
        lines = [
            f"Manifest: {preview.get('manifest_id')}",
            f"Target root: {preview.get('target_root')}",
            f"Can restore: {'yes' if preview.get('can_restore') else 'no'}",
            f"Will restore backups: {preview.get('restore_from_backup', 0)}",
            f"Will delete newly copied files: {preview.get('delete_copied_files', 0)}",
            f"Restore actions: {len(records)}",
        ]
        for warning in warnings:
            lines.append(f"WARNING: {warning}")
        for record in records:
            lines.append(f"- {record['destination_path']}: {record['action']}")
        return "\n".join(lines)

    @staticmethod
    def project_health_summary(audit: dict[str, object], manifests: list[dict[str, object]]) -> str:
        lines = [f"Project health: {audit['project_name']}", ""]
        for issue in audit["issues"]:
            lines.append(f"{issue['status'].upper():7} {issue['name']}: {issue['message']}")
        lines.extend(["", f"Manifests: {len(manifests)}"])
        for manifest in manifests[:5]:
            state = "restorable" if manifest.get("can_restore") else "blocked"
            lines.append(
                f"- {manifest.get('manifest_id')} ({manifest.get('target')}, {state}, "
                f"records={manifest.get('restorable')})"
            )
            for warning in manifest.get("warnings", []):
                lines.append(f"  WARNING: {warning}")
        return "\n".join(lines)

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
    def conflict_summary(plan) -> str:
        if not plan.conflicts:
            return "No destination conflicts detected."
        lines = [f"Destination conflicts: {len(plan.conflicts)}", ""]
        for conflict in plan.conflicts:
            lines.append(f"- {conflict.destination_path}")
            lines.append(f"  winner: {conflict.winning_mod}")
            lines.append(f"  mods: {', '.join(conflict.mods)}")
        return "\n".join(lines)

    @staticmethod
    def compact_conflict_summary(plan) -> str:
        if not plan.conflicts:
            return "No conflicts.\n\nStaging: safe\nGame apply: safe"
        top_paths = "\n".join(f"- {conflict.destination_path}" for conflict in plan.conflicts[:5])
        return "\n".join(
            [
                f"{len(plan.conflicts)} destination conflict(s)",
                "",
                "Staging: winning files overwrite staging only",
                "Game: existing files may be backed up and overwritten",
                "",
                "Top paths:",
                top_paths,
            ]
        )

    @staticmethod
    def apply_status_summary(plan) -> str:
        summary = summarize_deployment_plan(plan)
        return "\n".join(
            [
                "Staging: Ready",
                f"Winning operations: {summary['winning_operations']}",
                "",
                "Game Apply:",
                "Requires confirmation",
                f"Conflicts: {summary['conflicts']}",
                f"Warnings: {summary['warnings']}",
            ]
        )

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
        self._write_to(self.output, text)

    def _write_to(self, widget: tk.Text, text: str) -> None:
        widget.configure(state="normal")
        widget.delete("1.0", tk.END)
        widget.insert(tk.END, text)

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
        ttk.Button(
            controls,
            text="Create",
            command=lambda: self.create(copy_active=False),
        ).pack(side="left", padx=(8, 0))
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
