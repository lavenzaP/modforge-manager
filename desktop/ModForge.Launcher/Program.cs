using System.Diagnostics;
using System.Drawing.Drawing2D;
using System.IO.Compression;
using System.Security.Cryptography;
using System.Text.Json;
using System.Windows.Forms;

namespace ModForge.Launcher;

internal static class Program
{
    internal const string DefaultGameName = "Stellar Blade";
    internal static readonly string DefaultModsPath = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments), "ModForge Manager", "Games", DefaultGameName, "Mods");
    internal const string DefaultGamePath = @"C:\Program Files (x86)\Steam\steamapps\common\StellarBlade";

    [STAThread]
    private static int Main(string[] args)
    {
        if (args.Contains("--self-test", StringComparer.OrdinalIgnoreCase)) return SelfTest();

        var modsPath = ArgValue(args, "--mods") ?? DefaultModsPath;
        var gamePath = ArgValue(args, "--game") ?? DefaultGamePath;

        if (args.Contains("--smoke", StringComparer.OrdinalIgnoreCase))
        {
            var archiveImportErrors = MainForm.ImportArchivesInModsFolder(modsPath);
            var mods = Scanner.Scan(modsPath);
            var plan = VirtualPlanner.Build(mods.Where(mod => mod.Enabled), gamePath);
            WriteOutput(args, JsonSerializer.Serialize(new
            {
                modsPath,
                gamePath,
                steamAppId = MainForm.FindSteamAppId(gamePath),
                archiveImportErrors,
                modCount = mods.Count,
                enabledCount = mods.Count(mod => mod.Enabled),
                planEntries = plan.Entries.Count,
                winningFiles = plan.Winners.Count,
                conflicts = plan.Conflicts.Count,
                skippedFiles = plan.Skipped.Count,
                translationCandidates = TranslationInventory.Count(mods.Where(mod => mod.Enabled)),
            }));
            return 0;
        }

        if (args.Contains("--apply", StringComparer.OrdinalIgnoreCase))
        {
            var result = GameApplier.ApplyCurrentSelection(Scanner.Scan(modsPath).Where(mod => mod.Enabled).ToList(), gamePath, modsPath);
            WriteOutput(args, JsonSerializer.Serialize(result, new JsonSerializerOptions { WriteIndented = true }));
            return 0;
        }

        if (args.Contains("--undo", StringComparer.OrdinalIgnoreCase))
        {
            var result = GameApplier.UndoLatest(gamePath, modsPath);
            WriteOutput(args, JsonSerializer.Serialize(result, new JsonSerializerOptions { WriteIndented = true }));
            return 0;
        }

        ApplicationConfiguration.Initialize();
        Application.Run(new MainForm());
        return 0;
    }

    private static string? ArgValue(string[] args, string name)
    {
        var index = Array.FindIndex(args, item => item.Equals(name, StringComparison.OrdinalIgnoreCase));
        return index >= 0 && index + 1 < args.Length ? args[index + 1] : null;
    }

    private static void WriteOutput(string[] args, string json)
    {
        var outPath = ArgValue(args, "--out");
        if (outPath is null)
        {
            Console.WriteLine(json);
            return;
        }
        Directory.CreateDirectory(Path.GetDirectoryName(Path.GetFullPath(outPath))!);
        File.WriteAllText(outPath, json);
    }

    private static int SelfTest()
    {
        var root = Path.Combine(Path.GetTempPath(), "modforge-launcher-self-test-" + Guid.NewGuid().ToString("N"));
        try
        {
            var mods = Path.Combine(root, "mods");
            var game = Path.Combine(root, "game");
            Directory.CreateDirectory(mods);
            Directory.CreateDirectory(game);
            var shippingExe = Path.Combine(game, "SB", "Binaries", "Win64", "SB-Win64-Shipping.exe");
            Directory.CreateDirectory(Path.GetDirectoryName(shippingExe)!);
            File.WriteAllText(Path.Combine(game, "SB.exe"), "");
            File.WriteAllText(shippingExe, "");
            if (MainForm.FindGameExe(game) != shippingExe) return 9;
            if (MainForm.FindUnrealProjectFolder(game) != "SB") return 12;
            Directory.CreateDirectory(Path.Combine(mods, "A"));
            Directory.CreateDirectory(Path.Combine(mods, "B"));
            File.WriteAllText(Path.Combine(mods, "A", "same.json"), "a");
            File.WriteAllText(Path.Combine(mods, "B", "same.json"), "b");
            File.WriteAllText(Path.Combine(mods, "modforge-state.json"), "{\"Mods\":[{\"Name\":\"A\",\"Enabled\":true,\"Priority\":1},{\"Name\":\"A\",\"Enabled\":false,\"Priority\":2},{\"Name\":\" \",\"Enabled\":true,\"Priority\":3}]}");
            if (Scanner.Scan(mods).Count != 2) return 2;

            Scanner.SaveState(mods,
            [
                new ModRow { Name = "B", Enabled = true, Priority = 1 },
                new ModRow { Name = "A", Enabled = false, Priority = 2 },
            ]);

            var persisted = Scanner.Scan(mods);
            if (persisted.Count != 2 || persisted[0].Name != "B" || persisted[0].Priority != 1 || !persisted[0].Enabled || persisted[1].Name != "A" || persisted[1].Enabled) return 3;
            persisted[1].Enabled = true;
            persisted[0].Priority = 2;
            persisted[1].Priority = 1;
            Scanner.SaveState(mods, persisted);

            var scanned = Scanner.Scan(mods);
            var plan = VirtualPlanner.Build(scanned.Where(mod => mod.Enabled), game);
            if (scanned[0].Name != "A" || scanned[1].Name != "B") return 4;
            if (plan.Conflicts.Count != 1 || plan.Winners.Count != 1 || plan.Winners[0].ModName != "B") return 5;

            var target = Path.Combine(game, "SB", "Content", "Paks", "~mods", "same.json");
            Directory.CreateDirectory(Path.GetDirectoryName(target)!);
            File.WriteAllText(target, "vanilla");

            var applied = GameApplier.Apply(scanned, game, mods);
            if (applied.CopiedFiles != 1 || applied.OverwrittenFiles != 1) return 6;
            if (File.ReadAllText(target) != "b") return 7;

            var undone = GameApplier.UndoLatest(game, mods);
            if (undone.RestoredFiles != 1 || File.ReadAllText(target) != "vanilla") return 8;

            var genericGame = Path.Combine(root, "generic-game");
            var genericMod = Path.Combine(root, "generic-mod", "GenericPak");
            Directory.CreateDirectory(Path.Combine(genericGame, "GenericGame", "Content", "Paks"));
            Directory.CreateDirectory(Path.Combine(genericGame, "GenericGame", "Binaries", "Win64"));
            Directory.CreateDirectory(genericMod);
            File.WriteAllText(Path.Combine(genericGame, "GenericGame", "Binaries", "Win64", "GenericGame-Win64-Shipping.exe"), "");
            File.WriteAllText(Path.Combine(genericMod, "generic.pak"), "pak");
            var genericPlan = VirtualPlanner.Build([new ModRow { Name = "GenericPak", Enabled = true, Priority = 1, Path = genericMod }], genericGame);
            if (MainForm.FindUnrealProjectFolder(genericGame) != "GenericGame" || genericPlan.Winners.Single().DestinationRelative != "GenericGame/Content/Paks/~mods/generic.pak") return 13;

            var steamApps = Path.Combine(root, "Steam", "steamapps");
            var steamGame = Path.Combine(steamApps, "common", "Palworld");
            Directory.CreateDirectory(steamGame);
            File.WriteAllText(Path.Combine(steamApps, "appmanifest_1623730.acf"), "\"AppState\"\n{\n\t\"appid\"\t\t\"1623730\"\n\t\"installdir\"\t\t\"Palworld\"\n}\n");
            if (MainForm.FindSteamAppId(steamGame) != "1623730") return 16;

            var importMods = Path.Combine(root, "import-mods");
            var looseMod = Path.Combine(root, "loose-source", "LooseMod");
            Directory.CreateDirectory(looseMod);
            File.WriteAllText(Path.Combine(looseMod, "loose.pak"), "loose");
            MainForm.ImportMod(looseMod, importMods);
            if (!File.Exists(Path.Combine(importMods, "LooseMod", "loose.pak"))) return 14;

            var zipSource = Path.Combine(root, "zip-source");
            Directory.CreateDirectory(zipSource);
            File.WriteAllText(Path.Combine(zipSource, "zip.pak"), "zip");
            var zipPath = Path.Combine(root, "ZipMod.zip");
            ZipFile.CreateFromDirectory(zipSource, zipPath);
            MainForm.ImportMod(zipPath, importMods);
            if (!File.Exists(Path.Combine(importMods, "ZipMod", "zip.pak"))) return 15;

            GameApplier.Apply(scanned, game, mods);
            var syncedOff = GameApplier.ApplyCurrentSelection([], game, mods);
            if (syncedOff.RestoredFiles != 1 || File.ReadAllText(target) != "vanilla") return 11;

            GameApplier.Apply(scanned, game, mods);
            File.WriteAllText(target, "user-change");
            var skippedUndo = GameApplier.UndoLatest(game, mods);
            if (skippedUndo.SkippedFiles != 1 || File.ReadAllText(target) != "user-change") return 9;

            var batch = new[] { new ModRow { Enabled = true }, new ModRow { Enabled = false } };
            MainForm.ApplyBatchEnabled(batch, enabled: true);
            if (batch.Any(mod => !mod.Enabled)) return 10;
            return 0;
        }
        finally
        {
            if (Directory.Exists(root)) Directory.Delete(root, recursive: true);
        }
    }
}

internal sealed class MainForm : Form
{
    private readonly BindingSource _rows = new();
    private readonly DataGridView _grid = new();
    private readonly Label _summary = new();
    private readonly Label _status = new();
    private readonly TextBox _search = new() { PlaceholderText = "Search mods" };
    private readonly ComboBox _gamePicker = new() { DropDownStyle = ComboBoxStyle.DropDownList, Width = 260 };
    private readonly BindingSource _games = new();
    private readonly Button _apply = new() { Text = "Apply Changes" };
    private readonly Button _launch = new() { Text = "Launch Game" };
    private readonly List<ModRow> _mods = [];
    private readonly List<List<ModUiSnapshot>> _undoStack = [];
    private List<GameProfile> _profiles = [];
    private GameProfile _profile = new() { Name = Program.DefaultGameName, GamePath = Program.DefaultGamePath, ModsPath = Program.DefaultModsPath };
    private string _gamePath = "";
    private string _modsPath = "";
    private VirtualPlan _plan = VirtualPlan.Empty;
    private bool _switchingGame;

    public MainForm()
    {
        _profiles = GameProfileStore.Load();
        _profile = _profiles.FirstOrDefault(profile => profile.Selected) ?? _profiles[0];
        _gamePath = _profile.GamePath;
        _modsPath = _profile.ModsPath;
        Text = "ModForge Manager";
        MinimumSize = new Size(1120, 680);
        Size = new Size(1280, 760);
        Font = new Font("Segoe UI", 9F);
        BackColor = Color.FromArgb(248, 249, 251);
        AllowDrop = true;
        BuildUi();
        WireEvents();
        ScanMods();
    }

    private void BuildUi()
    {
        var root = new TableLayoutPanel
        {
            Dock = DockStyle.Fill,
            RowCount = 5,
            Padding = new Padding(16),
            BackColor = Color.FromArgb(246, 248, 251),
        };
        root.RowStyles.Add(new RowStyle(SizeType.AutoSize));
        root.RowStyles.Add(new RowStyle(SizeType.AutoSize));
        root.RowStyles.Add(new RowStyle(SizeType.AutoSize));
        root.RowStyles.Add(new RowStyle(SizeType.Percent, 100));
        root.RowStyles.Add(new RowStyle(SizeType.AutoSize));
        Controls.Add(root);

        var header = new TableLayoutPanel { Dock = DockStyle.Fill, AutoSize = true, ColumnCount = 7, Margin = new Padding(0, 0, 0, 12) };
        header.ColumnStyles.Add(new ColumnStyle(SizeType.AutoSize));
        header.ColumnStyles.Add(new ColumnStyle(SizeType.AutoSize));
        header.ColumnStyles.Add(new ColumnStyle(SizeType.AutoSize));
        header.ColumnStyles.Add(new ColumnStyle(SizeType.AutoSize));
        header.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100));
        header.ColumnStyles.Add(new ColumnStyle(SizeType.AutoSize));
        header.ColumnStyles.Add(new ColumnStyle(SizeType.AutoSize));
        header.Controls.Add(new Label
        {
            Text = "MF",
            AutoSize = false,
            Width = 38,
            Height = 34,
            TextAlign = ContentAlignment.MiddleCenter,
            Font = new Font(Font.FontFamily, 11F, FontStyle.Bold),
            BackColor = Color.FromArgb(225, 236, 255),
            ForeColor = Color.FromArgb(37, 99, 235),
            Margin = new Padding(0, 0, 10, 0),
        }, 0, 0);
        header.Controls.Add(new Label { Text = "ModForge Manager", AutoSize = true, Font = new Font(Font.FontFamily, 14F, FontStyle.Bold), Padding = new Padding(0, 5, 22, 0) }, 1, 0);
        _games.DataSource = _profiles;
        _gamePicker.DataSource = _games;
        _gamePicker.SelectedItem = _profile;
        _gamePicker.Margin = new Padding(0, 0, 8, 0);
        header.Controls.Add(_gamePicker, 2, 0);
        header.Controls.Add(Button("Change Game", ChangeGame, 112), 3, 0);
        header.Controls.Add(new Panel { Dock = DockStyle.Fill }, 4, 0);
        header.Controls.Add(Chip("Dry-run safe", Color.FromArgb(22, 101, 52), Color.FromArgb(220, 252, 231)), 5, 0);
        header.Controls.Add(_launch, 6, 0);
        root.Controls.Add(header, 0, 0);

        var toolbar = new TableLayoutPanel { Dock = DockStyle.Fill, AutoSize = true, ColumnCount = 9, Margin = new Padding(0, 0, 0, 10) };
        toolbar.ColumnStyles.Add(new ColumnStyle(SizeType.AutoSize));
        toolbar.ColumnStyles.Add(new ColumnStyle(SizeType.AutoSize));
        toolbar.ColumnStyles.Add(new ColumnStyle(SizeType.AutoSize));
        toolbar.ColumnStyles.Add(new ColumnStyle(SizeType.Percent, 100));
        toolbar.ColumnStyles.Add(new ColumnStyle(SizeType.AutoSize));
        toolbar.ColumnStyles.Add(new ColumnStyle(SizeType.AutoSize));
        toolbar.ColumnStyles.Add(new ColumnStyle(SizeType.AutoSize));
        toolbar.ColumnStyles.Add(new ColumnStyle(SizeType.AutoSize));
        toolbar.ColumnStyles.Add(new ColumnStyle(SizeType.AutoSize));
        toolbar.Controls.Add(Button("Add Mods", AddMods, 96), 0, 0);
        toolbar.Controls.Add(Button("Open Mods Folder", () => OpenFolder(_modsPath), 148), 1, 0);
        toolbar.Controls.Add(Button("Refresh", ScanMods, 84), 2, 0);
        _search.Width = 260;
        _search.Margin = new Padding(12, 0, 8, 0);
        toolbar.Controls.Add(_search, 3, 0);
        toolbar.Controls.Add(Button("Move Up", () => MoveSelected(-1), 88), 4, 0);
        toolbar.Controls.Add(Button("Move Down", () => MoveSelected(1), 100), 5, 0);
        toolbar.Controls.Add(_apply, 6, 0);
        toolbar.Controls.Add(MoreButton(), 7, 0);
        root.Controls.Add(toolbar, 0, 1);

        foreach (Button button in header.Controls.OfType<Button>().Concat(toolbar.Controls.OfType<Button>())) button.Height = 34;
        StyleButton(_launch, width: 156, back: Color.FromArgb(37, 99, 235), fore: Color.White);
        StyleButton(_apply, width: 128, back: Color.FromArgb(22, 163, 74), fore: Color.White);

        _summary.AutoSize = false;
        _summary.Height = 36;
        _summary.Dock = DockStyle.Fill;
        _summary.TextAlign = ContentAlignment.MiddleLeft;
        _summary.ForeColor = Color.FromArgb(67, 70, 85);
        _summary.BackColor = Color.White;
        _summary.Padding = new Padding(12, 0, 12, 0);
        root.Controls.Add(_summary, 0, 2);

        _grid.Dock = DockStyle.Fill;
        _grid.AutoGenerateColumns = false;
        _grid.AllowUserToAddRows = false;
        _grid.AllowUserToDeleteRows = false;
        _grid.AllowUserToResizeRows = false;
        _grid.MultiSelect = true;
        _grid.RowHeadersVisible = false;
        _grid.SelectionMode = DataGridViewSelectionMode.FullRowSelect;
        _grid.BackgroundColor = Color.White;
        _grid.BorderStyle = BorderStyle.FixedSingle;
        _grid.CellBorderStyle = DataGridViewCellBorderStyle.SingleHorizontal;
        _grid.GridColor = Color.FromArgb(229, 232, 239);
        _grid.RowTemplate.Height = 36;
        _grid.EnableHeadersVisualStyles = false;
        _grid.ColumnHeadersHeight = 38;
        _grid.ColumnHeadersDefaultCellStyle.BackColor = Color.FromArgb(250, 251, 253);
        _grid.ColumnHeadersDefaultCellStyle.ForeColor = Color.FromArgb(31, 41, 55);
        _grid.ColumnHeadersDefaultCellStyle.Font = new Font(Font.FontFamily, 9F, FontStyle.Bold);
        _grid.DefaultCellStyle.SelectionBackColor = Color.FromArgb(219, 234, 254);
        _grid.DefaultCellStyle.SelectionForeColor = Color.FromArgb(15, 23, 42);
        _grid.AlternatingRowsDefaultCellStyle.BackColor = Color.FromArgb(250, 251, 253);
        _grid.Columns.Add(new SwitchColumn { HeaderText = "On", DataPropertyName = nameof(ModRow.EnabledLabel), Width = 62, ReadOnly = true });
        _grid.Columns.Add(new DataGridViewTextBoxColumn { HeaderText = "Order", DataPropertyName = nameof(ModRow.Priority), Width = 70, ReadOnly = true });
        _grid.Columns.Add(new DataGridViewTextBoxColumn { HeaderText = "Mod", DataPropertyName = nameof(ModRow.Name), AutoSizeMode = DataGridViewAutoSizeColumnMode.Fill, FillWeight = 45, ReadOnly = true });
        _grid.Columns.Add(new DataGridViewTextBoxColumn { HeaderText = "Group", DataPropertyName = nameof(ModRow.ModSet), Width = 120, ReadOnly = true });
        _grid.Columns.Add(new DataGridViewTextBoxColumn { HeaderText = "State", DataPropertyName = nameof(ModRow.Status), Width = 150, ReadOnly = true });
        _grid.DataSource = _rows;
        root.Controls.Add(_grid, 0, 3);

        _status.Height = 28;
        _status.Dock = DockStyle.Fill;
        _status.TextAlign = ContentAlignment.MiddleLeft;
        _status.ForeColor = Color.FromArgb(67, 70, 85);
        _status.Padding = new Padding(4, 0, 0, 0);
        root.Controls.Add(_status, 0, 4);
    }

    private static Button Button(string text, Action action, int width)
    {
        var button = new Button { Text = text, Width = width };
        StyleButton(button, width, Color.White, Color.FromArgb(31, 41, 55));
        button.Click += (_, _) => action();
        return button;
    }

    private static void StyleButton(Button button, int width, Color back, Color fore)
    {
        button.Width = width;
        button.Height = 34;
        button.FlatStyle = FlatStyle.Flat;
        button.FlatAppearance.BorderColor = Color.FromArgb(214, 219, 228);
        button.FlatAppearance.BorderSize = 1;
        button.BackColor = back;
        button.ForeColor = fore;
        button.Margin = new Padding(4, 0, 4, 0);
    }

    private static Label Chip(string text, Color fore, Color back)
    {
        return new Label
        {
            Text = text,
            AutoSize = false,
            Width = 104,
            Height = 28,
            TextAlign = ContentAlignment.MiddleCenter,
            ForeColor = fore,
            BackColor = back,
            Margin = new Padding(0, 3, 12, 0),
        };
    }

    private Button MoreButton()
    {
        var button = new Button { Text = "More", Width = 70 };
        StyleButton(button, 70, Color.White, Color.FromArgb(31, 41, 55));
        var menu = new ContextMenuStrip();
        menu.Items.Add("Preview Changes", null, (_, _) => PreviewChanges());
        menu.Items.Add("Show Issues", null, (_, _) => ShowIssues());
        menu.Items.Add("Translation Inventory", null, (_, _) => ShowTranslationInventory());
        menu.Items.Add(new ToolStripSeparator());
        menu.Items.Add("Restore Last Apply", null, (_, _) => RestoreLastApply());
        menu.Items.Add("Change Game", null, (_, _) => ChangeGame());
        menu.Items.Add("Change Mods Folder", null, (_, _) => ChangeModsFolder());
        menu.Items.Add("Game Folder", null, (_, _) => OpenFolder(_gamePath));
        menu.Items.Add("Mods Folder", null, (_, _) => OpenFolder(_modsPath));
        menu.Items.Add("Backups", null, (_, _) => OpenFolder(Path.Combine(GameApplier.WorkspaceRoot(_modsPath), "backups")));
        menu.Items.Add("Manifest", null, (_, _) => OpenManifest());
        button.Click += (_, _) => menu.Show(button, new Point(0, button.Height));
        return button;
    }

    private void WireEvents()
    {
        _apply.Click += (_, _) => ApplyMods();
        _launch.Click += (_, _) => LaunchGame();
        _gamePicker.SelectedIndexChanged += (_, _) =>
        {
            if (_switchingGame || _gamePicker.SelectedItem is not GameProfile profile || ReferenceEquals(profile, _profile)) return;
            SwitchProfile(profile);
        };
        _search.TextChanged += (_, _) => RefreshGrid();
        _grid.CellFormatting += FormatGridCell;
        _grid.KeyDown += (_, e) =>
        {
            if (e.Control && e.KeyCode == Keys.Z)
            {
                UndoModListChange();
                e.Handled = true;
                e.SuppressKeyPress = true;
                return;
            }
            if (e.Control && e.KeyCode == Keys.A)
            {
                _grid.SelectAll();
                e.Handled = true;
                e.SuppressKeyPress = true;
                return;
            }
            if (e.KeyCode != Keys.Space || _grid.CurrentRow?.DataBoundItem is not ModRow row) return;
            var selected = SelectedMods();
            if (!selected.Contains(row)) selected.Add(row);
            PushUndo();
            ApplyBatchEnabled(selected, !row.Enabled);
            RefreshPlan();
            SaveModState();
            e.Handled = true;
            e.SuppressKeyPress = true;
        };
        _grid.CellClick += (_, e) =>
        {
            if (e.RowIndex < 0 || !IsOnColumn(e.ColumnIndex) || _grid.Rows[e.RowIndex].DataBoundItem is not ModRow row) return;
            PushUndo();
            row.Enabled = !row.Enabled;
            RefreshPlan();
            SaveModState();
        };
        _grid.CellValueChanged += (_, _) =>
        {
            RefreshPlan();
            SaveModState();
        };
        _grid.CurrentCellDirtyStateChanged += (_, _) =>
        {
            if (_grid.IsCurrentCellDirty) _grid.CommitEdit(DataGridViewDataErrorContexts.Commit);
        };
        DragEnter += (_, e) =>
        {
            if (e.Data?.GetDataPresent(DataFormats.FileDrop) == true) e.Effect = DragDropEffects.Copy;
        };
        DragDrop += DropMods;
    }

    private void FormatGridCell(object? sender, DataGridViewCellFormattingEventArgs e)
    {
        if (e.RowIndex < 0 || _grid.Rows[e.RowIndex].DataBoundItem is not ModRow row) return;
        if (_grid.Columns[e.ColumnIndex].DataPropertyName == nameof(ModRow.ModSet))
        {
            e.CellStyle.ForeColor = Color.FromArgb(37, 99, 235);
            e.CellStyle.Font = new Font(Font.FontFamily, 9F, FontStyle.Bold);
        }
        if (_grid.Columns[e.ColumnIndex].DataPropertyName == nameof(ModRow.EnabledLabel))
        {
            e.CellStyle.ForeColor = row.Enabled ? Color.FromArgb(22, 101, 52) : Color.FromArgb(107, 114, 128);
            e.CellStyle.Font = new Font(Font.FontFamily, 9F, FontStyle.Bold);
        }
        if (_grid.Columns[e.ColumnIndex].DataPropertyName == nameof(ModRow.Status))
        {
            e.CellStyle.ForeColor = row.Status.Contains("OK", StringComparison.OrdinalIgnoreCase)
                ? Color.FromArgb(22, 101, 52)
                : row.Status.Contains("No files", StringComparison.OrdinalIgnoreCase)
                    ? Color.FromArgb(180, 83, 9)
                    : Color.FromArgb(185, 28, 28);
            e.CellStyle.Font = new Font(Font.FontFamily, 9F, FontStyle.Bold);
        }
    }

    private void ScanMods()
    {
        var importErrors = ImportArchivesInModsFolder(_modsPath);
        _mods.Clear();
        _mods.AddRange(Scanner.Scan(_modsPath));
        RefreshPriorities();
        RefreshGrid();
        SetStatus(importErrors.Count > 0 ? importErrors[0] : $"Ready - {Short(_gamePath)} - {Short(_modsPath)}");
    }

    private void RefreshPlan()
    {
        _plan = VirtualPlanner.Build(_mods.Where(mod => mod.Enabled), _gamePath);
        var hasActiveApply = GameApplier.HasActiveApply(_gamePath, _modsPath);
        _apply.Enabled = _plan.Winners.Count > 0 || hasActiveApply;
        foreach (var mod in _mods)
        {
            mod.Status = _plan.Conflicts.Any(conflict => conflict.Mods.Contains(mod.Name))
                ? "Move preferred mod lower"
                : mod.FileCount == 0 ? "No files" : "OK";
        }
        _rows.ResetBindings(false);
        _grid.Invalidate();
        _summary.Text = hasActiveApply
            ? $"{_mods.Count(mod => mod.Enabled)} mods on - Apply Changes syncs on/off state to the game folder."
            : _plan.Conflicts.Count == 0
            ? $"{_mods.Count(mod => mod.Enabled)} mods on - {_plan.Winners.Count} files ready - game changes are protected."
            : $"{_plan.Conflicts.Count} issue(s): two mods edit the same file. Move the mod you want lower.";
    }

    private void RefreshGrid()
    {
        var query = _search.Text.Trim();
        var source = string.IsNullOrWhiteSpace(query)
            ? _mods
            : _mods.Where(mod =>
                mod.Name.Contains(query, StringComparison.OrdinalIgnoreCase)
                || mod.ModSet.Contains(query, StringComparison.OrdinalIgnoreCase)
                || mod.Status.Contains(query, StringComparison.OrdinalIgnoreCase)).ToList();
        if (!ReferenceEquals(_rows.DataSource, source)) _rows.DataSource = source;
        _rows.ResetBindings(false);
        RefreshPlan();
    }

    private void RefreshPriorities()
    {
        for (var i = 0; i < _mods.Count; i++) _mods[i].Priority = i + 1;
    }

    private void MoveSelected(int delta)
    {
        if (_grid.CurrentRow?.DataBoundItem is not ModRow row) return;
        var index = _mods.IndexOf(row);
        var next = index + delta;
        if (index < 0 || next < 0 || next >= _mods.Count) return;
        PushUndo();
        (_mods[index], _mods[next]) = (_mods[next], _mods[index]);
        RefreshPriorities();
        RefreshGrid();
        SaveModState();
        SelectRow(row);
    }

    private void SelectRow(ModRow row)
    {
        foreach (DataGridViewRow gridRow in _grid.Rows)
        {
            if (!ReferenceEquals(gridRow.DataBoundItem, row)) continue;
            gridRow.Selected = true;
            _grid.CurrentCell = gridRow.Cells[0];
            return;
        }
    }

    private void AddMods()
    {
        using var dialog = new OpenFileDialog
        {
            Title = "Add mod files",
            Multiselect = true,
            Filter = "Mod files (*.pak;*.ucas;*.utoc;*.zip;*.rar;*.7z)|*.pak;*.ucas;*.utoc;*.zip;*.rar;*.7z|All files (*.*)|*.*",
        };
        if (dialog.ShowDialog(this) != DialogResult.OK) return;
        Directory.CreateDirectory(_modsPath);
        try
        {
            foreach (var file in dialog.FileNames) ImportMod(file, _modsPath);
        }
        catch (Exception ex)
        {
            MessageBox.Show(this, ex.Message, "Add Mods failed", MessageBoxButtons.OK, MessageBoxIcon.Error);
        }
        ScanMods();
        SaveModState();
    }

    private void DropMods(object? sender, DragEventArgs e)
    {
        if (e.Data?.GetData(DataFormats.FileDrop) is not string[] paths) return;
        Directory.CreateDirectory(_modsPath);
        try
        {
            foreach (var path in paths) ImportMod(path, _modsPath);
        }
        catch (Exception ex)
        {
            MessageBox.Show(this, ex.Message, "Add Mods failed", MessageBoxButtons.OK, MessageBoxIcon.Error);
        }
        ScanMods();
        SaveModState();
    }

    private void ApplyMods()
    {
        try
        {
            var result = GameApplier.ApplyCurrentSelection(_mods.Where(mod => mod.Enabled).ToList(), _gamePath, _modsPath);
            SetStatus($"Synced game folder - copied {result.CopiedFiles}, restored {result.RestoredFiles}, deleted {result.DeletedFiles}");
            RefreshPlan();
            MessageBox.Show(this, $"Game folder updated.\nCopied: {result.CopiedFiles}\nRestored: {result.RestoredFiles}\nDeleted: {result.DeletedFiles}", "Apply Changes", MessageBoxButtons.OK, MessageBoxIcon.Information);
        }
        catch (Exception ex)
        {
            MessageBox.Show(this, ex.Message, "Apply failed", MessageBoxButtons.OK, MessageBoxIcon.Error);
            SetStatus("Apply failed - game was not launched");
        }
    }

    private void RestoreLastApply()
    {
        var answer = MessageBox.Show(this, "Restore the game folder to the state before the latest ModForge apply?", "Restore Last Apply", MessageBoxButtons.YesNo, MessageBoxIcon.Warning);
        if (answer != DialogResult.Yes) return;
        var result = GameApplier.UndoLatest(_gamePath, _modsPath);
        SetStatus($"Restore complete - restored {result.RestoredFiles}, deleted {result.DeletedFiles}, skipped {result.SkippedFiles}");
        RefreshPlan();
        if (result.SkippedFiles > 0)
        {
            MessageBox.Show(this, "Restore skipped changed files. ModForge only restores files that still match the last apply manifest.", "Restore skipped", MessageBoxButtons.OK, MessageBoxIcon.Warning);
        }
    }

    private void PreviewChanges()
    {
        var lines = _plan.Winners.Take(25).Select(entry => $"{entry.ModName} -> {entry.DestinationRelative}");
        MessageBox.Show(this, $"{_plan.Winners.Count} files will be copied.\n{_plan.Conflicts.Count} conflicts.\n{_plan.Skipped.Count} skipped.\n\n{string.Join("\n", lines)}", "Preview Changes");
    }

    private void ShowIssues()
    {
        if (_plan.Conflicts.Count == 0 && _plan.Skipped.Count == 0)
        {
            MessageBox.Show(this, "No issues in the current plan.", "Issues");
            return;
        }
        var conflicts = _plan.Conflicts.Select(item => $"{item.FileName}\nWinner: {item.Winner}\nMods: {string.Join(", ", item.Mods)}");
        var skipped = _plan.Skipped.Take(20).Select(item => $"Skipped: {item.ModName} - {item.SourceRelative}");
        MessageBox.Show(this, string.Join("\n\n", conflicts.Concat(skipped)), "Issues");
    }

    private void ShowTranslationInventory()
    {
        var items = TranslationInventory.Find(_mods.Where(mod => mod.Enabled)).Take(40).ToList();
        MessageBox.Show(this, $"{items.Count} candidate text files shown.\n\n{string.Join("\n", items)}", "Translation Inventory");
    }

    private void OpenManifest()
    {
        var path = GameApplier.LatestManifestPath(_modsPath);
        if (File.Exists(path)) Process.Start(new ProcessStartInfo(path) { UseShellExecute = true });
        else MessageBox.Show(this, "No apply manifest yet.", "Manifest");
    }

    private void LaunchGame()
    {
        var steamAppId = FindSteamAppId(_gamePath);
        if (steamAppId is not null)
        {
            Process.Start(new ProcessStartInfo($"steam://rungameid/{steamAppId}") { UseShellExecute = true });
            SetStatus($"Launching through Steam - app {steamAppId}");
            return;
        }

        var exe = FindGameExe(_gamePath);
        if (exe is null)
        {
            MessageBox.Show(this, "Could not find the game executable.", "Launch Game");
            return;
        }
        Process.Start(new ProcessStartInfo(exe) { UseShellExecute = true, WorkingDirectory = Path.GetDirectoryName(exe) });
        SetStatus("Launching directly - Steam app was not detected");
    }

    private void ChangeGame()
    {
        using var dialog = new FolderBrowserDialog { Description = "Choose an Unreal game folder", SelectedPath = Directory.Exists(_gamePath) ? _gamePath : Program.DefaultGamePath };
        if (dialog.ShowDialog(this) != DialogResult.OK) return;
        var gamePath = dialog.SelectedPath;
        if (FindUnrealProjectFolder(gamePath) is null)
        {
            MessageBox.Show(this, "That folder does not look like an Unreal game. Choose the folder that contains the game's Content/Paks or Binaries/Win64 folder.", "Change Game", MessageBoxButtons.OK, MessageBoxIcon.Warning);
            return;
        }

        var existing = _profiles.FirstOrDefault(profile => SamePath(profile.GamePath, gamePath));
        var profile = existing ?? new GameProfile
        {
            Name = FriendlyGameName(gamePath),
            GamePath = gamePath,
            ModsPath = GameProfileStore.DefaultModsPathFor(FriendlyGameName(gamePath)),
        };
        if (existing is null) _profiles.Add(profile);
        SwitchProfile(profile);
    }

    private void ChangeModsFolder()
    {
        using var dialog = new FolderBrowserDialog { Description = "Choose this game's mods folder", SelectedPath = _modsPath };
        if (dialog.ShowDialog(this) != DialogResult.OK) return;
        SaveModState();
        _profile.ModsPath = dialog.SelectedPath;
        _modsPath = _profile.ModsPath;
        GameProfileStore.Save(_profiles, _profile);
        ScanMods();
    }

    private void SwitchProfile(GameProfile profile)
    {
        SaveModState();
        _profile = profile;
        _gamePath = profile.GamePath;
        _modsPath = profile.ModsPath;
        GameProfileStore.Save(_profiles, _profile);
        RefreshGamePicker();
        ScanMods();
    }

    private void RefreshGamePicker()
    {
        _switchingGame = true;
        _games.DataSource = null;
        _games.DataSource = _profiles;
        _gamePicker.SelectedItem = _profile;
        _switchingGame = false;
    }

    private void SaveModState()
    {
        if (_mods.Count > 0) Scanner.SaveState(_modsPath, _mods);
    }

    private List<ModRow> SelectedMods()
    {
        return _grid.SelectedRows
            .Cast<DataGridViewRow>()
            .Select(gridRow => gridRow.DataBoundItem)
            .OfType<ModRow>()
            .Distinct()
            .ToList();
    }

    private bool IsOnColumn(int columnIndex) => columnIndex >= 0 && _grid.Columns[columnIndex].DataPropertyName == nameof(ModRow.EnabledLabel);

    internal static void ApplyBatchEnabled(IEnumerable<ModRow> mods, bool enabled)
    {
        foreach (var mod in mods) mod.Enabled = enabled;
    }

    private void PushUndo()
    {
        _undoStack.Add(_mods.Select(mod => new ModUiSnapshot(mod.Path, mod.Enabled, mod.Priority)).ToList());
        if (_undoStack.Count > 20) _undoStack.RemoveAt(0);
    }

    private void UndoModListChange()
    {
        if (_undoStack.Count == 0)
        {
            SetStatus("Nothing to undo");
            return;
        }

        var snapshot = _undoStack[^1];
        _undoStack.RemoveAt(_undoStack.Count - 1);
        var byPath = _mods.ToDictionary(mod => mod.Path, StringComparer.OrdinalIgnoreCase);
        var restored = new List<ModRow>();
        foreach (var item in snapshot.OrderBy(item => item.Priority))
        {
            if (!byPath.TryGetValue(item.Path, out var mod)) continue;
            mod.Enabled = item.Enabled;
            restored.Add(mod);
        }
        restored.AddRange(_mods.Except(restored).OrderBy(mod => mod.Priority));
        _mods.Clear();
        _mods.AddRange(restored);
        RefreshPriorities();
        RefreshGrid();
        SaveModState();
        SetStatus("Undo complete - mod list state restored");
    }

    private static void OpenFolder(string path)
    {
        Directory.CreateDirectory(path);
        Process.Start(new ProcessStartInfo(path) { UseShellExecute = true });
    }

    internal static string? FindGameExe(string gameRoot)
    {
        if (!Directory.Exists(gameRoot)) return null;
        var directWin64 = Path.Combine(gameRoot, "Binaries", "Win64");
        var directShipping = Directory.Exists(directWin64)
            ? Directory.EnumerateFiles(directWin64, "*-Win64-Shipping.exe", SearchOption.TopDirectoryOnly).OrderBy(path => path.Length).FirstOrDefault()
            : null;
        if (directShipping is not null) return directShipping;

        foreach (var project in Directory.EnumerateDirectories(gameRoot))
        {
            var win64 = Path.Combine(project, "Binaries", "Win64");
            if (!Directory.Exists(win64)) continue;
            var shipping = Directory.EnumerateFiles(win64, "*-Win64-Shipping.exe", SearchOption.TopDirectoryOnly).OrderBy(path => path.Length).FirstOrDefault();
            if (shipping is not null) return shipping;
        }

        var stellarCandidates = new[]
        {
            Path.Combine(gameRoot, "SB", "Binaries", "Win64", "SB-Win64-Shipping.exe"),
            Path.Combine(gameRoot, "SB.exe"),
            Path.Combine(gameRoot, "StellarBlade.exe"),
        };
        return stellarCandidates.FirstOrDefault(File.Exists)
            ?? Directory.EnumerateFiles(gameRoot, "*.exe", SearchOption.TopDirectoryOnly).OrderBy(path => path.Length).FirstOrDefault();
    }

    internal static string? FindSteamAppId(string gameRoot)
    {
        if (!Directory.Exists(gameRoot)) return null;
        var fullGameRoot = Path.GetFullPath(gameRoot).TrimEnd('\\');
        var installDir = Path.GetFileName(fullGameRoot);
        var steamApps = Directory.GetParent(fullGameRoot)?.Parent?.FullName;
        if (steamApps is null || !Directory.Exists(steamApps) || !Path.GetFileName(steamApps).Equals("steamapps", StringComparison.OrdinalIgnoreCase)) return null;

        foreach (var manifest in Directory.EnumerateFiles(steamApps, "appmanifest_*.acf"))
        {
            var appId = AcfValue(manifest, "appid");
            var manifestInstallDir = AcfValue(manifest, "installdir");
            if (string.IsNullOrWhiteSpace(appId) || !installDir.Equals(manifestInstallDir, StringComparison.OrdinalIgnoreCase)) continue;
            return appId;
        }
        return null;
    }

    private static string? AcfValue(string path, string key)
    {
        foreach (var line in File.ReadLines(path))
        {
            var trimmed = line.Trim();
            if (!trimmed.StartsWith($"\"{key}\"", StringComparison.OrdinalIgnoreCase)) continue;
            var parts = trimmed.Split('"', StringSplitOptions.RemoveEmptyEntries);
            return parts.Length >= 2 ? parts[^1] : null;
        }
        return null;
    }

    internal static string? FindUnrealProjectFolder(string gameRoot)
    {
        if (!Directory.Exists(gameRoot)) return null;
        if (Directory.Exists(Path.Combine(gameRoot, "Content", "Paks")) || Directory.Exists(Path.Combine(gameRoot, "Binaries", "Win64"))) return "";

        var exe = FindGameExe(gameRoot);
        if (exe is not null && Path.GetDirectoryName(exe) is { } exeDir)
        {
            var project = Directory.GetParent(exeDir)?.Parent;
            if (project is not null && SamePath(Directory.GetParent(project.FullName)?.FullName ?? "", gameRoot)) return project.Name;
        }

        foreach (var project in Directory.EnumerateDirectories(gameRoot))
        {
            if (Directory.Exists(Path.Combine(project, "Content", "Paks")) || Directory.Exists(Path.Combine(project, "Binaries", "Win64"))) return Path.GetFileName(project);
        }
        return null;
    }

    private static void CopyDirectory(string source, string destination)
    {
        foreach (var file in Directory.EnumerateFiles(source, "*", SearchOption.AllDirectories))
        {
            var target = Path.Combine(destination, Path.GetRelativePath(source, file));
            Directory.CreateDirectory(Path.GetDirectoryName(target)!);
            File.Copy(file, target, overwrite: true);
        }
    }

    internal static void ImportMod(string path, string modsPath)
    {
        Directory.CreateDirectory(modsPath);
        if (Directory.Exists(path))
        {
            CopyDirectory(path, Path.Combine(modsPath, Path.GetFileName(path)));
            return;
        }
        if (!File.Exists(path)) return;
        if (IsSupportedArchive(path))
        {
            ExtractArchiveMod(path, modsPath);
            return;
        }
        File.Copy(path, Path.Combine(modsPath, Path.GetFileName(path)), overwrite: true);
    }

    internal static List<string> ImportArchivesInModsFolder(string modsPath)
    {
        if (!Directory.Exists(modsPath)) return [];
        var errors = new List<string>();
        foreach (var archive in Directory.EnumerateFiles(modsPath).Where(IsSupportedArchive).ToList())
        {
            try
            {
                ExtractArchiveMod(archive, modsPath);
                File.Delete(archive);
            }
            catch (Exception ex)
            {
                errors.Add($"Could not extract {Path.GetFileName(archive)} - {ex.Message}");
            }
        }
        return errors;
    }

    private static bool IsSupportedArchive(string path)
    {
        var ext = Path.GetExtension(path);
        return ext.Equals(".zip", StringComparison.OrdinalIgnoreCase)
            || ext.Equals(".rar", StringComparison.OrdinalIgnoreCase)
            || ext.Equals(".7z", StringComparison.OrdinalIgnoreCase);
    }

    private static void ExtractArchiveMod(string archivePath, string modsPath)
    {
        var target = Path.Combine(modsPath, Path.GetFileNameWithoutExtension(archivePath));
        var temp = Path.Combine(Path.GetTempPath(), "modforge-extract-" + Guid.NewGuid().ToString("N"));
        try
        {
            if (Path.GetExtension(archivePath).Equals(".zip", StringComparison.OrdinalIgnoreCase)) ExtractZipSafe(archivePath, temp);
            else ExtractWithTarSafe(archivePath, temp);
            if (Directory.Exists(target)) Directory.Delete(target, recursive: true);
            if (File.Exists(target)) File.Delete(target);
            CopyDirectory(temp, target);
        }
        finally
        {
            if (Directory.Exists(temp)) Directory.Delete(temp, recursive: true);
        }
    }

    private static void ExtractWithTarSafe(string archivePath, string destination)
    {
        ValidateTarEntries(archivePath);
        Directory.CreateDirectory(destination);
        RunTar(["-xf", archivePath, "-C", destination]);
    }

    private static void ValidateTarEntries(string archivePath)
    {
        var output = RunTar(["-tf", archivePath]);
        foreach (var raw in output.Split(['\r', '\n'], StringSplitOptions.RemoveEmptyEntries))
        {
            var entry = raw.Trim().Replace('\\', '/');
            if (entry.StartsWith("/") || entry.Contains(':') || entry.Split('/').Any(part => part == ".."))
            {
                throw new InvalidOperationException($"Unsafe archive entry: {raw}");
            }
        }
    }

    private static string RunTar(IReadOnlyList<string> args)
    {
        using var process = new Process();
        var tar = Path.Combine(Environment.SystemDirectory, "tar.exe");
        process.StartInfo.FileName = File.Exists(tar) ? tar : "tar";
        process.StartInfo.UseShellExecute = false;
        process.StartInfo.CreateNoWindow = true;
        process.StartInfo.RedirectStandardOutput = true;
        process.StartInfo.RedirectStandardError = true;
        foreach (var arg in args) process.StartInfo.ArgumentList.Add(arg);
        process.Start();
        var output = process.StandardOutput.ReadToEnd();
        var error = process.StandardError.ReadToEnd();
        process.WaitForExit();
        if (process.ExitCode != 0) throw new InvalidOperationException($"Windows could not extract this archive. Use .zip or extract it first. {error.Trim()}");
        return output;
    }

    private static void ExtractZipSafe(string zipPath, string destination)
    {
        var root = Path.GetFullPath(destination).TrimEnd('\\') + "\\";
        using var archive = ZipFile.OpenRead(zipPath);
        foreach (var entry in archive.Entries)
        {
            var target = Path.GetFullPath(Path.Combine(root, entry.FullName.Replace('/', Path.DirectorySeparatorChar)));
            if (!target.StartsWith(root, StringComparison.OrdinalIgnoreCase)) throw new InvalidOperationException($"Unsafe zip entry: {entry.FullName}");
            if (string.IsNullOrEmpty(entry.Name))
            {
                Directory.CreateDirectory(target);
                continue;
            }
            Directory.CreateDirectory(Path.GetDirectoryName(target)!);
            entry.ExtractToFile(target, overwrite: true);
        }
    }

    private static string Short(string path) => Path.GetFileName(path.TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar));
    private static string FriendlyGameName(string path) => Path.GetFileName(path.TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar));
    private static bool SamePath(string left, string right) => Path.GetFullPath(left).TrimEnd('\\').Equals(Path.GetFullPath(right).TrimEnd('\\'), StringComparison.OrdinalIgnoreCase);
    private void SetStatus(string value) => _status.Text = value;
}

internal sealed class ModRow
{
    public int Priority { get; set; }
    public bool Enabled { get; set; } = true;
    public string EnabledLabel => Enabled ? "On" : "Off";
    public string Name { get; set; } = "";
    public string ModSet { get; set; } = "Misc";
    public string Status { get; set; } = "OK";
    public string Path { get; set; } = "";
    public int FileCount { get; set; }
}

internal sealed class GameProfile
{
    public string Name { get; set; } = "";
    public string GamePath { get; set; } = "";
    public string ModsPath { get; set; } = "";
    public bool Selected { get; set; }
    public override string ToString() => Name;
}

internal sealed class GameProfileConfig
{
    public List<GameProfile> Games { get; set; } = [];
}

internal static class GameProfileStore
{
    private static readonly string ConfigPath = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData), "ModForge Manager", "games.json");

    public static List<GameProfile> Load()
    {
        try
        {
            if (File.Exists(ConfigPath))
            {
                var config = JsonSerializer.Deserialize<GameProfileConfig>(File.ReadAllText(ConfigPath));
                var games = config?.Games.Where(IsValid).ToList() ?? [];
                if (games.Count > 0) return games;
            }
        }
        catch (JsonException)
        {
        }

        return
        [
            new GameProfile
            {
                Name = Program.DefaultGameName,
                GamePath = Program.DefaultGamePath,
                ModsPath = Program.DefaultModsPath,
                Selected = true,
            },
        ];
    }

    public static void Save(List<GameProfile> games, GameProfile selected)
    {
        foreach (var game in games) game.Selected = ReferenceEquals(game, selected);
        Directory.CreateDirectory(Path.GetDirectoryName(ConfigPath)!);
        File.WriteAllText(ConfigPath, JsonSerializer.Serialize(new GameProfileConfig { Games = games.Where(IsValid).ToList() }, new JsonSerializerOptions { WriteIndented = true }));
    }

    public static string DefaultModsPathFor(string gameName) => Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments), "ModForge Manager", "Games", SafeName(gameName), "Mods");

    private static bool IsValid(GameProfile profile) => !string.IsNullOrWhiteSpace(profile.Name) && !string.IsNullOrWhiteSpace(profile.GamePath) && !string.IsNullOrWhiteSpace(profile.ModsPath);

    private static string SafeName(string value)
    {
        var invalid = Path.GetInvalidFileNameChars().ToHashSet();
        var cleaned = new string(value.Select(ch => invalid.Contains(ch) ? '_' : ch).ToArray()).Trim();
        return string.IsNullOrWhiteSpace(cleaned) ? "Unreal Game" : cleaned;
    }
}

internal sealed class SwitchColumn : DataGridViewTextBoxColumn
{
    public SwitchColumn()
    {
        CellTemplate = new SwitchCell();
    }
}

internal sealed class SwitchCell : DataGridViewTextBoxCell
{
    protected override void Paint(Graphics graphics, Rectangle clipBounds, Rectangle cellBounds, int rowIndex, DataGridViewElementStates cellState, object? value, object? formattedValue, string? errorText, DataGridViewCellStyle cellStyle, DataGridViewAdvancedBorderStyle advancedBorderStyle, DataGridViewPaintParts paintParts)
    {
        base.Paint(graphics, clipBounds, cellBounds, rowIndex, cellState, value, formattedValue, errorText, cellStyle, advancedBorderStyle, paintParts & ~DataGridViewPaintParts.ContentForeground);
        var enabled = string.Equals(Convert.ToString(value), "On", StringComparison.OrdinalIgnoreCase)
            || string.Equals(Convert.ToString(formattedValue), "On", StringComparison.OrdinalIgnoreCase);
        var width = 38;
        var height = 20;
        var bounds = new Rectangle(cellBounds.Left + (cellBounds.Width - width) / 2, cellBounds.Top + (cellBounds.Height - height) / 2, width, height);
        using var back = new SolidBrush(enabled ? Color.FromArgb(37, 99, 235) : Color.FromArgb(209, 213, 219));
        using var knob = new SolidBrush(Color.White);
        using var path = Pill(bounds);
        graphics.SmoothingMode = SmoothingMode.AntiAlias;
        graphics.FillPath(back, path);
        var knobSize = 16;
        var knobX = enabled ? bounds.Right - knobSize - 2 : bounds.Left + 2;
        graphics.FillEllipse(knob, knobX, bounds.Top + 2, knobSize, knobSize);
    }

    private static GraphicsPath Pill(Rectangle rect)
    {
        var radius = rect.Height;
        var path = new GraphicsPath();
        path.AddArc(rect.Left, rect.Top, radius, radius, 90, 180);
        path.AddArc(rect.Right - radius, rect.Top, radius, radius, 270, 180);
        path.CloseFigure();
        return path;
    }
}

internal sealed record ModUiSnapshot(string Path, bool Enabled, int Priority);

internal static class Scanner
{
    private const string StateFileName = "modforge-state.json";

    public static List<ModRow> Scan(string modsPath)
    {
        MainForm.ImportArchivesInModsFolder(modsPath);
        if (!Directory.Exists(modsPath)) return [];
        var saved = LoadState(modsPath).Mods
            .Where(item => !string.IsNullOrWhiteSpace(item.Name))
            .GroupBy(item => item.Name, StringComparer.OrdinalIgnoreCase)
            .ToDictionary(group => group.Key, group => group.Last(), StringComparer.OrdinalIgnoreCase);
        return Directory.EnumerateFileSystemEntries(modsPath)
            .Where(IsModEntry)
            .OrderBy(path => saved.TryGetValue(ModName(path), out var entry) ? entry.Priority : int.MaxValue)
            .ThenBy(path => ModName(path), StringComparer.OrdinalIgnoreCase)
            .Select((path, index) =>
            {
                var name = ModName(path);
                return new ModRow
                {
                    Priority = index + 1,
                    Enabled = !saved.TryGetValue(name, out var state) || state.Enabled,
                    Name = name,
                    ModSet = GroupFor(name),
                    Path = path,
                    FileCount = File.Exists(path) ? 1 : Directory.EnumerateFiles(path, "*", SearchOption.AllDirectories).Count(),
                };
            })
            .ToList();
    }

    public static void SaveState(string modsPath, IEnumerable<ModRow> mods)
    {
        Directory.CreateDirectory(modsPath);
        var state = new ModForgeState
        {
            Mods = mods
                .Where(mod => !string.IsNullOrWhiteSpace(mod.Name))
                .OrderBy(mod => mod.Priority)
                .GroupBy(mod => mod.Name, StringComparer.OrdinalIgnoreCase)
                .Select(group => group.Last())
                .Select(mod => new ModStateEntry { Name = mod.Name, Enabled = mod.Enabled, Priority = mod.Priority })
                .ToList(),
        };
        File.WriteAllText(StatePath(modsPath), JsonSerializer.Serialize(state, new JsonSerializerOptions { WriteIndented = true }));
    }

    private static ModForgeState LoadState(string modsPath)
    {
        var path = StatePath(modsPath);
        if (!File.Exists(path)) return new ModForgeState();
        try
        {
            return JsonSerializer.Deserialize<ModForgeState>(File.ReadAllText(path)) ?? new ModForgeState();
        }
        catch (JsonException)
        {
            return new ModForgeState();
        }
    }

    private static string StatePath(string modsPath) => Path.Combine(modsPath, StateFileName);

    private static bool IsModEntry(string path)
    {
        var name = Path.GetFileName(path);
        return !name.Equals(StateFileName, StringComparison.OrdinalIgnoreCase)
            && !name.StartsWith(".")
            && !name.EndsWith("_separator", StringComparison.OrdinalIgnoreCase);
    }

    private static string ModName(string path) => Directory.Exists(path) ? Path.GetFileName(path) : Path.GetFileNameWithoutExtension(path);

    private static string GroupFor(string name)
    {
        if (name.Contains("CNS", StringComparison.OrdinalIgnoreCase) || name.Contains("suit", StringComparison.OrdinalIgnoreCase) || name.Contains("skin", StringComparison.OrdinalIgnoreCase)) return "Visuals";
        if (name.Contains("UE4SS", StringComparison.OrdinalIgnoreCase) || name.Contains("required", StringComparison.OrdinalIgnoreCase) || name.Contains("core", StringComparison.OrdinalIgnoreCase)) return "Core";
        if (name.Contains("sprint", StringComparison.OrdinalIgnoreCase) || name.Contains("camera", StringComparison.OrdinalIgnoreCase)) return "Gameplay";
        return "Misc";
    }
}

internal sealed class ModForgeState
{
    public List<ModStateEntry> Mods { get; set; } = [];
}

internal sealed class ModStateEntry
{
    public string Name { get; set; } = "";
    public bool Enabled { get; set; } = true;
    public int Priority { get; set; }
}

internal sealed record PlanEntry(string ModName, int Priority, string SourcePath, string SourceRelative, string DestinationRelative);
internal sealed record PlanSkipped(string ModName, string SourceRelative);
internal sealed record ConflictInfo(string FileName, string Winner, List<string> Mods);
internal sealed record VirtualPlan(List<PlanEntry> Entries, List<PlanEntry> Winners, List<ConflictInfo> Conflicts, List<PlanSkipped> Skipped)
{
    public static VirtualPlan Empty { get; } = new([], [], [], []);
}

internal static class VirtualPlanner
{
    private static readonly string[] PackageExtensions = [".pak", ".ucas", ".utoc"];
    private static readonly HashSet<string> RuntimeDlls = new(StringComparer.OrdinalIgnoreCase)
    {
        "dwmapi.dll", "ue4ss.dll", "version.dll", "winhttp.dll", "xinput1_3.dll", "xinput1_4.dll", "xinput9_1_0.dll",
    };

    public static VirtualPlan Build(IEnumerable<ModRow> mods, string gameRoot)
    {
        var entries = new List<PlanEntry>();
        var skipped = new List<PlanSkipped>();
        var projectFolder = MainForm.FindUnrealProjectFolder(gameRoot) ?? "";
        foreach (var mod in mods.OrderBy(mod => mod.Priority))
        {
            foreach (var source in Files(mod.Path))
            {
                var relative = File.Exists(mod.Path) ? Path.GetFileName(source) : Path.GetRelativePath(mod.Path, source).Replace('\\', '/');
                var destination = MapDestination(relative, projectFolder);
                if (destination is null)
                {
                    skipped.Add(new PlanSkipped(mod.Name, relative));
                    continue;
                }
                entries.Add(new PlanEntry(mod.Name, mod.Priority, source, relative, destination));
            }
        }

        var groups = entries.GroupBy(entry => entry.DestinationRelative, StringComparer.OrdinalIgnoreCase).ToList();
        var winners = groups.Select(group => group.OrderBy(entry => entry.Priority).Last()).ToList();
        var conflicts = groups
            .Where(group => group.Select(entry => entry.ModName).Distinct(StringComparer.OrdinalIgnoreCase).Count() > 1)
            .Select(group =>
            {
                var ordered = group.OrderBy(entry => entry.Priority).ToList();
                return new ConflictInfo(group.Key, ordered.Last().ModName, ordered.Select(entry => entry.ModName).Distinct(StringComparer.OrdinalIgnoreCase).ToList());
            })
            .ToList();
        return new VirtualPlan(entries, winners, conflicts, skipped);
    }

    private static IEnumerable<string> Files(string path)
    {
        if (File.Exists(path))
        {
            if (!Ignored(Path.GetFileName(path))) yield return path;
            yield break;
        }
        foreach (var file in Directory.EnumerateFiles(path, "*", SearchOption.AllDirectories))
        {
            if (!Ignored(Path.GetFileName(file))) yield return file;
        }
    }

    private static string? MapDestination(string relative, string projectFolder)
    {
        var normalized = relative.Replace('\\', '/').TrimStart('/');
        var name = Path.GetFileName(normalized);
        var ext = Path.GetExtension(name);
        if (Ignored(name)) return null;
        if (!string.IsNullOrWhiteSpace(projectFolder) && normalized.StartsWith($"{projectFolder}/", StringComparison.OrdinalIgnoreCase)) return normalized;
        if (normalized.StartsWith("Content/Paks/", StringComparison.OrdinalIgnoreCase) || normalized.StartsWith("Binaries/Win64/", StringComparison.OrdinalIgnoreCase)) return UnrealPath(projectFolder, normalized);
        if (normalized.StartsWith("ue4ss/", StringComparison.OrdinalIgnoreCase)) return UnrealPath(projectFolder, $"Binaries/Win64/{normalized}");
        if (!normalized.Contains('/') && RuntimeDlls.Contains(name)) return UnrealPath(projectFolder, $"Binaries/Win64/{name}");
        if (PackageExtensions.Contains(ext, StringComparer.OrdinalIgnoreCase) || ext.Equals(".json", StringComparison.OrdinalIgnoreCase)) return UnrealPath(projectFolder, $"Content/Paks/~mods/{name}");
        return null;
    }

    private static string UnrealPath(string projectFolder, string relative) => string.IsNullOrWhiteSpace(projectFolder) ? relative : $"{projectFolder}/{relative}";

    private static bool Ignored(string name)
    {
        return name.Equals("mod_manifest.json", StringComparison.OrdinalIgnoreCase)
            || name.Equals("manifest.json", StringComparison.OrdinalIgnoreCase)
            || name.Equals("meta.ini", StringComparison.OrdinalIgnoreCase)
            || name.StartsWith("readme", StringComparison.OrdinalIgnoreCase);
    }
}

internal static class GameApplier
{
    public static GameApplyResult ApplyCurrentSelection(IReadOnlyList<ModRow> mods, string gameRoot, string modsPath)
    {
        var restored = 0;
        var deleted = 0;
        if (HasActiveApply(gameRoot, modsPath))
        {
            var undo = UndoLatest(gameRoot, modsPath);
            if (undo.SkippedFiles > 0)
            {
                throw new InvalidOperationException("Some applied files changed outside ModForge. Restore or clean them before applying new changes.");
            }
            restored = undo.RestoredFiles;
            deleted = undo.DeletedFiles;
        }

        if (mods.Count == 0) return new GameApplyResult(0, 0, 0, restored, deleted, "", "");

        var result = Apply(mods, gameRoot, modsPath);
        return result with { RestoredFiles = restored, DeletedFiles = deleted };
    }

    public static GameApplyResult Apply(IReadOnlyList<ModRow> mods, string gameRoot, string modsPath)
    {
        if (!Directory.Exists(gameRoot)) throw new DirectoryNotFoundException($"Game folder not found: {gameRoot}");
        if (File.Exists(LatestManifestPath(modsPath)))
        {
            throw new InvalidOperationException("A previous ModForge apply is still active. Use Apply Changes to sync the current mod list.");
        }

        var plan = VirtualPlanner.Build(mods, gameRoot);
        var applyId = DateTime.Now.ToString("yyyyMMdd-HHmmss-fffffff") + "-" + Guid.NewGuid().ToString("N")[..8];
        var backupRoot = Path.Combine(WorkspaceRoot(modsPath), "backups", applyId);
        var manifestPath = Path.Combine(WorkspaceRoot(modsPath), "manifests", $"{applyId}-game-apply.json");
        Directory.CreateDirectory(backupRoot);

        var copied = 0;
        var overwritten = 0;
        var backups = new List<GameApplyBackup>();
        var written = new List<GameApplyFile>();
        var manifest = new GameApplyManifest
        {
            ApplyId = applyId,
            Status = "InProgress",
            CreatedAt = DateTimeOffset.Now,
            GamePath = gameRoot,
            ModsPath = modsPath,
            BackupRoot = backupRoot,
            Files = written,
            Backups = backups,
        };
        WriteManifestAtomic(manifestPath, manifest);

        try
        {
            foreach (var entry in plan.Winners)
            {
                var destination = FullPathInside(gameRoot, entry.DestinationRelative);
                if (File.Exists(destination))
                {
                    var backup = FullPathInside(backupRoot, entry.DestinationRelative);
                    Directory.CreateDirectory(Path.GetDirectoryName(backup)!);
                    File.Copy(destination, backup, overwrite: true);
                    backups.Add(new GameApplyBackup
                    {
                        DestinationRelative = entry.DestinationRelative,
                        BackupSha256 = Sha256(backup),
                        BackupLength = new FileInfo(backup).Length,
                    });
                    overwritten++;
                }
                Directory.CreateDirectory(Path.GetDirectoryName(destination)!);
                File.Copy(entry.SourcePath, destination, overwrite: true);
                written.Add(new GameApplyFile
                {
                    ModName = entry.ModName,
                    Priority = entry.Priority,
                    SourcePath = entry.SourcePath,
                    SourceRelative = entry.SourceRelative,
                    DestinationRelative = entry.DestinationRelative,
                    WrittenSha256 = Sha256(destination),
                    WrittenLength = new FileInfo(destination).Length,
                });
                copied++;
            }

            manifest.Status = "Succeeded";
            WriteManifestAtomic(manifestPath, manifest);
            WriteManifestAtomic(LatestManifestPath(modsPath), manifest);
        }
        catch
        {
            RollBack(gameRoot, backupRoot, written, backups);
            manifest.Status = "Failed";
            TryWriteManifest(manifestPath, manifest);
            throw;
        }

        return new GameApplyResult(copied, overwritten, plan.Skipped.Count, 0, 0, backupRoot, manifestPath);
    }

    public static UndoResult UndoLatest(string gameRoot, string modsPath)
    {
        var manifestPath = LatestManifestPath(modsPath);
        if (!File.Exists(manifestPath)) return new UndoResult(0, 0, 0);

        var manifest = JsonSerializer.Deserialize<GameApplyManifest>(File.ReadAllText(manifestPath));
        if (manifest is null || !SamePath(manifest.GamePath, gameRoot)) return new UndoResult(0, 0, 0);

        var files = manifest.Files
            .GroupBy(file => file.DestinationRelative, StringComparer.OrdinalIgnoreCase)
            .Select(group => group.Last())
            .ToList();
        var unsafeCount = files.Count(file => !CanUndo(gameRoot, manifest.BackupRoot, manifest.Backups, file));
        if (unsafeCount > 0) return new UndoResult(0, 0, unsafeCount);

        var restored = 0;
        var deleted = 0;
        foreach (var file in files)
        {
            var destination = FullPathInside(gameRoot, file.DestinationRelative);
            var backup = FullPathInside(manifest.BackupRoot, file.DestinationRelative);
            if (File.Exists(backup))
            {
                Directory.CreateDirectory(Path.GetDirectoryName(destination)!);
                File.Copy(backup, destination, overwrite: true);
                restored++;
            }
            else if (File.Exists(destination))
            {
                File.Delete(destination);
                deleted++;
            }
        }
        File.Delete(manifestPath);
        return new UndoResult(restored, deleted, 0);
    }

    public static bool HasActiveApply(string gameRoot, string modsPath)
    {
        var manifestPath = LatestManifestPath(modsPath);
        if (!File.Exists(manifestPath)) return false;
        var manifest = JsonSerializer.Deserialize<GameApplyManifest>(File.ReadAllText(manifestPath));
        return manifest is null || SamePath(manifest.GamePath, gameRoot);
    }

    public static string WorkspaceRoot(string modsPath)
    {
        var full = Path.GetFullPath(modsPath);
        return Path.Combine(Directory.GetParent(full)?.FullName ?? full, ".modforge");
    }

    public static string LatestManifestPath(string modsPath) => Path.Combine(WorkspaceRoot(modsPath), "manifests", "latest-game-apply.json");

    private static void RollBack(string gameRoot, string backupRoot, List<GameApplyFile> written, List<GameApplyBackup> backups)
    {
        var backedUp = backups.Select(item => item.DestinationRelative).ToHashSet(StringComparer.OrdinalIgnoreCase);
        foreach (var file in written.AsEnumerable().Reverse())
        {
            var destination = FullPathInside(gameRoot, file.DestinationRelative);
            var backup = FullPathInside(backupRoot, file.DestinationRelative);
            if (backedUp.Contains(file.DestinationRelative) && File.Exists(backup))
            {
                File.Copy(backup, destination, overwrite: true);
            }
            else if (File.Exists(destination))
            {
                File.Delete(destination);
            }
        }
    }

    private static bool CanUndo(string gameRoot, string backupRoot, List<GameApplyBackup> backups, GameApplyFile file)
    {
        var destination = FullPathInside(gameRoot, file.DestinationRelative);
        if (!Matches(destination, file.WrittenSha256, file.WrittenLength, allowMissingWhenLegacy: true)) return false;

        var backup = FullPathInside(backupRoot, file.DestinationRelative);
        var backupRecord = backups.FirstOrDefault(item => item.DestinationRelative.Equals(file.DestinationRelative, StringComparison.OrdinalIgnoreCase));
        return backupRecord is null || Matches(backup, backupRecord.BackupSha256, backupRecord.BackupLength, allowMissingWhenLegacy: true);
    }

    private static bool Matches(string path, string? sha256, long length, bool allowMissingWhenLegacy)
    {
        if (string.IsNullOrWhiteSpace(sha256)) return allowMissingWhenLegacy || File.Exists(path);
        if (!File.Exists(path)) return false;
        var info = new FileInfo(path);
        if (info.Length != length) return false;
        return Sha256(path).Equals(sha256, StringComparison.OrdinalIgnoreCase);
    }

    private static void WriteManifestAtomic(string path, GameApplyManifest manifest)
    {
        Directory.CreateDirectory(Path.GetDirectoryName(path)!);
        var tempPath = path + ".tmp";
        var json = JsonSerializer.Serialize(manifest, new JsonSerializerOptions { WriteIndented = true });
        File.WriteAllText(tempPath, json);
        File.Move(tempPath, path, overwrite: true);
    }

    private static void TryWriteManifest(string path, GameApplyManifest manifest)
    {
        try
        {
            WriteManifestAtomic(path, manifest);
        }
        catch
        {
        }
    }

    private static string Sha256(string path)
    {
        using var stream = File.OpenRead(path);
        using var sha = SHA256.Create();
        return Convert.ToHexString(sha.ComputeHash(stream));
    }

    private static string FullPathInside(string root, string relative)
    {
        var fullRoot = Path.GetFullPath(root).TrimEnd('\\') + "\\";
        var fullPath = Path.GetFullPath(Path.Combine(fullRoot, relative.Replace('/', Path.DirectorySeparatorChar)));
        if (!fullPath.StartsWith(fullRoot, StringComparison.OrdinalIgnoreCase)) throw new InvalidOperationException($"Refusing to write outside root: {fullPath}");
        return fullPath;
    }

    private static bool SamePath(string left, string right) => Path.GetFullPath(left).TrimEnd('\\').Equals(Path.GetFullPath(right).TrimEnd('\\'), StringComparison.OrdinalIgnoreCase);
}

internal sealed record GameApplyResult(int CopiedFiles, int OverwrittenFiles, int SkippedFiles, int RestoredFiles, int DeletedFiles, string BackupRoot, string ManifestPath);
internal sealed record UndoResult(int RestoredFiles, int DeletedFiles, int SkippedFiles);

internal sealed class GameApplyManifest
{
    public string ApplyId { get; set; } = "";
    public string Status { get; set; } = "Succeeded";
    public DateTimeOffset CreatedAt { get; set; }
    public string GamePath { get; set; } = "";
    public string ModsPath { get; set; } = "";
    public string BackupRoot { get; set; } = "";
    public List<GameApplyFile> Files { get; set; } = [];
    public List<GameApplyBackup> Backups { get; set; } = [];
}

internal sealed class GameApplyFile
{
    public string ModName { get; set; } = "";
    public int Priority { get; set; }
    public string SourcePath { get; set; } = "";
    public string SourceRelative { get; set; } = "";
    public string DestinationRelative { get; set; } = "";
    public string? WrittenSha256 { get; set; }
    public long WrittenLength { get; set; }
}

internal sealed class GameApplyBackup
{
    public string DestinationRelative { get; set; } = "";
    public string? BackupSha256 { get; set; }
    public long BackupLength { get; set; }
}

internal static class TranslationInventory
{
    private static readonly string[] Extensions = [".json", ".csv", ".txt", ".ini", ".lua", ".locres", ".locmeta"];

    public static int Count(IEnumerable<ModRow> mods) => Find(mods).Count();

    public static IEnumerable<string> Find(IEnumerable<ModRow> mods)
    {
        foreach (var mod in mods)
        {
            if (!Directory.Exists(mod.Path)) continue;
            foreach (var file in Directory.EnumerateFiles(mod.Path, "*", SearchOption.AllDirectories))
            {
                if (Extensions.Contains(Path.GetExtension(file), StringComparer.OrdinalIgnoreCase))
                {
                    yield return $"{mod.Name}: {Path.GetRelativePath(mod.Path, file)}";
                }
            }
        }
    }
}
