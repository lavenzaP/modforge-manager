using System;
using System.Collections.Generic;
using System.IO;
using System.Text.Json;
using Microsoft.UI;
using Microsoft.UI.Dispatching;
using Microsoft.UI.Windowing;
using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
using Microsoft.UI.Xaml.Media;
using Windows.Graphics;
using Windows.UI;
using Windows.UI.Text;

namespace ModForge.WinUI;

public sealed partial class MainWindow : Window
{
    private readonly List<ModRow> mods;
    private readonly List<ConflictRow> conflicts;
    private readonly List<string> warnings;
    private AppWindow? appWindow;
    private DispatcherQueueTimer? windowSizeSaveTimer;
    private SizeInt32 pendingWindowSize;
    private WorkflowState workflowState = WorkflowState.NoProject;
    private string activePage = "Home";
    private string selectedFamily = "Not selected";
    private string statusMessage = "Start Guided Setup to open a project safely.";
    private bool planReviewManuallyChecked;
    private bool gameApplyConfirmationChecked;

    public MainWindow()
    {
        InitializeComponent();
        Title = "ModForge Manager";
        mods = CreateMods();
        conflicts = CreateConflicts();
        warnings = CreateWarnings();
        ConfigureWindowPersistence();
        ShellNav.SelectedItem = NavHome;
        ShowPage("Home");
    }

    private void OpenProjectButton_Click(object sender, RoutedEventArgs e)
    {
        AdvanceState(WorkflowState.ProjectOpened, "Project opened. Choose a mod family next.");
        ShowPage("Guided Setup");
    }

    private void ScanButton_Click(object sender, RoutedEventArgs e)
    {
        AdvanceState(WorkflowState.Scanned, "Scan complete. No files were changed.");
        ShowPage("Mods");
    }

    private void PlanButton_Click(object sender, RoutedEventArgs e)
    {
        AdvanceState(WorkflowState.PlanReady, "Plan is ready. Review conflicts before staging.");
        ShowPage("Plan");
    }

    private void ApplyButton_Click(object sender, RoutedEventArgs e)
    {
        ShowPage("Apply & Restore");
        if (HasReached(WorkflowState.RestoreAvailable))
        {
            SetStatus("Restore manifest is available. Preview restore or view the latest manifest.");
        }
        else if (HasReached(WorkflowState.Staged))
        {
            SetStatus("Game apply requires explicit confirmation in Apply & Restore.");
        }
        else
        {
            SetStatus("Apply to game is locked until staging is complete.");
        }
    }

    private void ShellNav_SelectionChanged(NavigationView sender, NavigationViewSelectionChangedEventArgs args)
    {
        if (args.SelectedItemContainer?.Tag is string page)
        {
            ShowPage(page);
        }
    }

    private void ShowPage(string page)
    {
        activePage = page;
        ContentHost.Children.Clear();

        if (page == "Home")
        {
            PageTitle.Text = "Home";
            PageSubtitle.Text = "WinUI 3 primary candidate shell with safe workflow gates.";
            ContentHost.Children.Add(BuildHome());
        }
        else if (page == "Guided Setup")
        {
            PageTitle.Text = "Guided Setup";
            PageSubtitle.Text = "Completed, current, and locked steps from the shared workflow state.";
            ContentHost.Children.Add(BuildGuidedSetup());
        }
        else if (page == "Mods")
        {
            PageTitle.Text = "Mods";
            PageSubtitle.Text = HasReached(WorkflowState.Scanned)
                ? "Review scanned mods and selected-mod details."
                : "No real scan has been run yet.";
            ContentHost.Children.Add(BuildMods());
        }
        else if (page == "Plan")
        {
            PageTitle.Text = "Plan";
            PageSubtitle.Text = "Review conflicts and warnings before staging.";
            ContentHost.Children.Add(BuildPlan());
        }
        else if (page == "Apply & Restore")
        {
            PageTitle.Text = "Apply & Restore";
            PageSubtitle.Text = "Staging first, game apply behind explicit confirmation.";
            ContentHost.Children.Add(BuildApplyRestore());
        }
        else
        {
            PageTitle.Text = "Tools";
            PageSubtitle.Text = "Optional checks run only when requested.";
            ContentHost.Children.Add(BuildTools());
        }

        UpdateShell();
    }

    private UIElement BuildHome()
    {
        var grid = TwoColumnGrid(1.45, 1.0);
        var left = Stack();
        Grid.SetColumn(left, 0);
        grid.Children.Add(left);

        var hero = Panel(Stack(
            Text(HasReached(WorkflowState.ProjectOpened) ? "Ready for the next safe action" : "No project open", 28, SemiBoldWeight, White),
            Spaced(HasReached(WorkflowState.ProjectOpened)
                ? "Continue through the gated workflow. The shell will not scan, run Python, stage, or write game files until a matching action is unlocked."
                : "Open a project or start Guided Setup. No scan, Python process, staging, or game write happens at startup.", 14, Secondary),
            ButtonRow(
                PrimaryButton(HasReached(WorkflowState.ProjectOpened) ? "Continue Guided Setup" : "Start Guided Setup", AccentBlue, (_, _) => ShowPage("Guided Setup")),
                PrimaryButton("Open Project", AccentGreen, (_, _) => { AdvanceState(WorkflowState.ProjectOpened, "Project opened. Choose a mod family next."); ShowPage("Guided Setup"); })),
            NextActionCard()));
        left.Children.Add(hero);

        left.Children.Add(SectionTitle("Workflow progress"));
        left.Children.Add(WorkflowStepper());

        var right = Stack();
        Grid.SetColumn(right, 1);
        grid.Children.Add(right);
        right.Children.Add(ProjectSummaryPanel());
        right.Children.Add(InfoPanel("Shell decision", new[]
        {
            "WinUI 3 is now the primary Windows shell candidate.",
            "WPF remains the fallback until WinUI packaging is proven.",
            "Python CLI/core remains the trusted behavior source.",
            "No Python bundling or new mod features are included in this pass."
        }));
        return grid;
    }

    private UIElement BuildGuidedSetup()
    {
        var steps = Stack();
        steps.Children.Add(Text("Interactive setup", 22, SemiBoldWeight, White));
        steps.Children.Add(Spaced("Work left to right through each row. Locked actions stay disabled until the shared workflow state reaches the prerequisite.", 13, Secondary));
        steps.Children.Add(CompactWizardStep(1, "Choose mod family", "Pick REFramework, Unreal, or Godot/STS2.", FamilyButtons(), WorkflowState.ModFamilyChosen, WorkflowState.NoProject));
        steps.Children.Add(CompactWizardStep(2, "Select game folder", "Choose the game root. No writes happen while selecting.", WizardButton("Choose game folder", IsCurrentStep(WorkflowState.GameFolderSelected, WorkflowState.ModFamilyChosen), (_, _) => { AdvanceState(WorkflowState.GameFolderSelected, "Game folder selected."); ShowPage("Guided Setup"); }), WorkflowState.GameFolderSelected, WorkflowState.ModFamilyChosen));
        steps.Children.Add(CompactWizardStep(3, "Select mods folder", "Choose the folder or archive collection to inspect.", WizardButton("Choose mods folder", IsCurrentStep(WorkflowState.ModsFolderSelected, WorkflowState.GameFolderSelected), (_, _) => { AdvanceState(WorkflowState.ModsFolderSelected, "Mods folder selected. Scan is now available."); ShowPage("Guided Setup"); }), WorkflowState.ModsFolderSelected, WorkflowState.GameFolderSelected));
        steps.Children.Add(CompactWizardStep(4, "Scan mods", "Read-only scan. No files will be changed.", WizardButton("Scan now", IsCurrentStep(WorkflowState.Scanned, WorkflowState.ModsFolderSelected), (_, _) => { AdvanceState(WorkflowState.Scanned, "Scan complete. Review the Mods page."); ShowPage("Mods"); }), WorkflowState.Scanned, WorkflowState.ModsFolderSelected));
        steps.Children.Add(CompactWizardStep(5, "Review plan and conflicts", "Inspect winners, overwritten destinations, and warnings.", WizardButton("Open plan review", IsCurrentStep(WorkflowState.PlanReady, WorkflowState.Scanned), (_, _) => { AdvanceState(WorkflowState.PlanReady, "Plan is ready for review."); ShowPage("Plan"); }), WorkflowState.PlanReviewed, WorkflowState.Scanned));
        steps.Children.Add(CompactWizardStep(6, "Apply to staging", "First write step. The game folder is still untouched.", WizardButton(StagingActionLabel(), CanApplyToStaging(), (_, _) => { AdvanceState(WorkflowState.Staged, "Applied to staging. Game apply can now be confirmed."); ShowPage("Apply & Restore"); }), WorkflowState.Staged, WorkflowState.PlanReviewed));
        steps.Children.Add(CompactWizardStep(7, "Apply to game", "Requires staging plus explicit confirmation.", WizardButton(HasReached(WorkflowState.RestoreAvailable) ? "Restore ready" : "Open game apply", HasReached(WorkflowState.Staged) && !HasReached(WorkflowState.RestoreAvailable), (_, _) => { ShowPage("Apply & Restore"); SetStatus("Confirm game apply from Apply & Restore."); }), WorkflowState.RestoreAvailable, WorkflowState.Staged));

        return Panel(steps);
    }

    private UIElement BuildMods()
    {
        if (!HasReached(WorkflowState.Scanned))
        {
            return EmptyActionPage(
                "No scan results yet.",
                "Select a mod family, game folder, and mods folder before scanning. Scan is read-only and does not change files.",
                "Scan Mods",
                CanScan(),
                (_, _) => { AdvanceState(WorkflowState.Scanned, "Scan complete. Mod results are ready."); ShowPage("Mods"); },
                new[] { StepStateText("Project", WorkflowState.ProjectOpened), StepStateText("Family", WorkflowState.ModFamilyChosen), StepStateText("Game folder", WorkflowState.GameFolderSelected), StepStateText("Mods folder", WorkflowState.ModsFolderSelected) });
        }

        var grid = TwoColumnGrid(1.75, 1.0);
        var list = new ListView
        {
            SelectionMode = ListViewSelectionMode.Single,
            Background = Brush("#0F1721"),
            BorderBrush = Brush("#243141"),
            BorderThickness = new Thickness(1),
            CornerRadius = new CornerRadius(8)
        };
        foreach (var mod in mods)
        {
            list.Items.Add(ModListRow(mod));
        }

        var left = Stack(
            KpiRow(),
            HeaderRow(new[] { "Enabled", "Priority", "Mod Name", "Family", "Status", "Conflicts" }),
            list);
        Grid.SetColumn(left, 0);
        grid.Children.Add(left);

        var detailPanel = Panel(SelectedModPanel(mods[0]));
        Grid.SetColumn(detailPanel, 1);
        grid.Children.Add(detailPanel);

        list.SelectionChanged += (_, _) =>
        {
            if (list.SelectedIndex >= 0 && list.SelectedIndex < mods.Count)
            {
                detailPanel.Child = SelectedModPanel(mods[list.SelectedIndex]);
            }
        };
        list.SelectedIndex = 0;
        return grid;
    }

    private UIElement BuildPlan()
    {
        if (!HasReached(WorkflowState.PlanReady))
        {
            return EmptyActionPage(
                "No plan generated yet.",
                "Run a scan first, then create the plan. The plan is the review contract before staging unlocks.",
                "Create plan",
                CanCreatePlan(),
                (_, _) => { AdvanceState(WorkflowState.PlanReady, "Plan is ready. Review required."); ShowPage("Plan"); },
                new[] { StepStateText("Scan", WorkflowState.Scanned), "Plan review: pending", "Staging: locked" });
        }

        var grid = TwoColumnGrid(1.45, 1.0);
        var left = Stack();
        Grid.SetColumn(left, 0);
        grid.Children.Add(left);
        left.Children.Add(Panel(Stack(
            Text("Plan Summary", 22, SemiBoldWeight, White),
            Line("Copy to staging", "1,842 files", AccentGreen),
            Line("Destination conflicts", "5 conflicts affecting 4 mods", AccentRed),
            Line("Warnings", "3 review items", AccentAmber))));

        left.Children.Add(SectionTitle("Conflict list"));
        left.Children.Add(HeaderRow(new[] { "Destination", "Winning Mod", "Losing Mod", "Risk" }));
        var conflictList = new ListView { Background = Brush("#0F1721"), BorderBrush = Brush("#243141"), BorderThickness = new Thickness(1), CornerRadius = new CornerRadius(8) };
        foreach (var conflict in conflicts)
        {
            conflictList.Items.Add(ConflictListRow(conflict));
        }
        left.Children.Add(conflictList);

        var right = Stack();
        Grid.SetColumn(right, 1);
        grid.Children.Add(right);
        right.Children.Add(InfoPanel("Warnings", warnings));

        var checkbox = new CheckBox
        {
            Content = "I reviewed the conflict and warning lists",
            Foreground = White,
            IsChecked = planReviewManuallyChecked,
            IsEnabled = !planReviewManuallyChecked && !HasReached(WorkflowState.Staged),
            Margin = new Thickness(0, 14, 0, 12)
        };
        var staging = PrimaryButton(StagingActionLabel(), AccentGreen, (_, _) => { AdvanceState(WorkflowState.Staged, "Applied to staging. Game apply is now available."); ShowPage("Apply & Restore"); });
        staging.IsEnabled = CanApplyToStaging();
        checkbox.Checked += (_, _) =>
        {
            planReviewManuallyChecked = true;
            AdvanceState(WorkflowState.PlanReviewed, "Plan review complete. Apply to staging is unlocked.");
            ShowPage("Plan");
        };
        right.Children.Add(Panel(Stack(
            Text("Review gate", 20, SemiBoldWeight, White),
            Spaced("Apply to staging unlocks only after manual review confirmation.", 13, Secondary),
            checkbox,
            staging)));
        return grid;
    }

    private UIElement BuildApplyRestore()
    {
        if (!HasReached(WorkflowState.PlanReady))
        {
            return EmptyActionPage(
                "Apply & Restore is locked.",
                "Create and review a plan before staging, game apply, manifests, or restore actions become available.",
                "Open Plan",
                CanCreatePlan(),
                (_, _) => { AdvanceState(WorkflowState.PlanReady, "Plan is ready. Review required."); ShowPage("Plan"); },
                new[] { StepStateText("Scan", WorkflowState.Scanned), "Plan: required", "Staging: locked", "Restore: locked" });
        }

        var grid = TwoColumnGrid(1.1, 1.0);
        var left = Stack();
        Grid.SetColumn(left, 0);
        grid.Children.Add(left);

        var staging = PrimaryButton(StagingActionLabel(), AccentGreen, (_, _) => { AdvanceState(WorkflowState.Staged, "Applied to staging. Game apply now requires explicit confirmation."); ShowPage("Apply & Restore"); });
        staging.IsEnabled = CanApplyToStaging();
        var openStaging = PrimaryButton("Open staging folder", AccentBlue, (_, _) => SetStatus("Staging folder can be opened after staging is complete."));
        openStaging.IsEnabled = HasReached(WorkflowState.Staged);
        left.Children.Add(Panel(Stack(
            Text("Staging actions", 22, SemiBoldWeight, White),
            Spaced("Staging writes to the configured staging folder first. It does not touch the game folder.", 13, Secondary),
            ButtonRow(staging, openStaging))));

        left.Children.Add(GameApplyPanel());

        var right = Stack();
        Grid.SetColumn(right, 1);
        grid.Children.Add(right);
        right.Children.Add(ManifestPanel());

        var preview = PrimaryButton("Preview restore", AccentBlue, (_, _) => SetStatus("Restore preview opened."));
        var selected = PrimaryButton("Restore selected files", AccentAmber, (_, _) => SetStatus("Selected restore requires a manifest selection."));
        var all = PrimaryButton("Restore all from latest", AccentRed, (_, _) => SetStatus("Full restore stays behind a confirmation dialog."));
        preview.IsEnabled = selected.IsEnabled = all.IsEnabled = HasReached(WorkflowState.RestoreAvailable);
        right.Children.Add(Panel(Stack(
            Text("Restore actions", 20, SemiBoldWeight, White),
            Spaced("Restore remains manifest-bound. Preview before restoring selected files or a full manifest.", 13, Secondary),
            ButtonRow(preview, selected, all))));
        return grid;
    }

    private UIElement GameApplyPanel()
    {
        var stack = Stack();
        var title = HasReached(WorkflowState.RestoreAvailable) ? "Restore manifest available" : "Game apply confirm zone";
        stack.Children.Add(Text(title, 22, SemiBoldWeight, HasReached(WorkflowState.Staged) ? AccentRed : White));

        if (!HasReached(WorkflowState.Staged))
        {
            var locked = PrimaryButton("Confirm game apply locked", Brush("#243141"), (_, _) => SetStatus("Apply to staging first, then confirm game apply."));
            locked.IsEnabled = false;
            stack.Children.Add(Spaced("Game apply stays locked until a staging manifest exists.", 13, Secondary));
            stack.Children.Add(ButtonRow(locked));
        }
        else if (HasReached(WorkflowState.RestoreAvailable))
        {
            stack.Children.Add(Spaced("Game apply is complete. The primary actions are now manifest inspection and restore preview.", 13, Secondary));
            stack.Children.Add(ButtonRow(
                PrimaryButton("View latest manifest", AccentBlue, (_, _) => SetStatus("Latest manifest is ready for inspection.")),
                PrimaryButton("Preview restore", AccentGreen, (_, _) => SetStatus("Restore preview is ready."))));
        }
        else
        {
            var confirm = PrimaryButton("Confirm game apply", AccentRed, (_, _) => { AdvanceState(WorkflowState.RestoreAvailable, "Game apply complete. Restore manifest is available."); ShowPage("Apply & Restore"); });
            confirm.IsEnabled = gameApplyConfirmationChecked;
            var checkbox = new CheckBox
            {
                Content = "I understand this writes staged files to the game folder",
                Foreground = White,
                IsChecked = gameApplyConfirmationChecked,
                Margin = new Thickness(0, 14, 0, 12)
            };
            checkbox.Checked += (_, _) => { gameApplyConfirmationChecked = true; confirm.IsEnabled = true; SetStatus("Explicit confirmation received. Confirm game apply is unlocked."); };
            checkbox.Unchecked += (_, _) => { gameApplyConfirmationChecked = false; confirm.IsEnabled = false; SetStatus("Confirm game apply is locked until the confirmation box is checked."); };
            stack.Children.Add(Spaced("This action writes to the game folder. Confirm explicitly before the button unlocks.", 13, Secondary));
            stack.Children.Add(checkbox);
            stack.Children.Add(ButtonRow(confirm, PrimaryButton("View staging manifest", AccentBlue, (_, _) => SetStatus("Staging manifest is ready for inspection."))));
        }

        var panel = Panel(stack);
        panel.Margin = new Thickness(0, 16, 0, 0);
        panel.BorderBrush = HasReached(WorkflowState.Staged) ? AccentRed : Brush("#243141");
        return panel;
    }

    private UIElement BuildTools()
    {
        return TwoColumnGrid(1.2, 1.0,
            Panel(Stack(
                Text("Tool status", 22, SemiBoldWeight, White),
                HeaderRow(new[] { "Tool", "Status", "Detail" }),
                ToolRow("7-Zip", "Not configured", "Optional archive inspection."),
                ToolRow("UnrealPak", "Not configured", "Optional extraction, not archive-as-is deployment."),
                ToolRow("Godot PCK Tool", "Not configured", "Optional PCK inspection."),
                ToolRow("Python Sidecar", "Idle", "No Python process starts until requested."))),
            Panel(Stack(
                Text("Tool checks", 22, SemiBoldWeight, White),
                Spaced("Tool checks are optional and run only when you request them.", 13, Secondary),
                PrimaryButton("Check Python Sidecar", AccentBlue, (_, _) => SetStatus("Python sidecar idle. No Python process was launched at startup.")))));
    }

    private UIElement FamilyButtons()
    {
        return ButtonRow(
            WizardButton("REFramework", true, (_, _) => SelectFamily("REFramework")),
            WizardButton("Unreal ~mods", true, (_, _) => SelectFamily("Unreal Mods")),
            WizardButton("Godot / STS2", true, (_, _) => SelectFamily("Godot / STS2")));
    }

    private void SelectFamily(string family)
    {
        selectedFamily = family;
        AdvanceState(WorkflowState.ModFamilyChosen, family + " workflow selected. Choose the game folder next.");
        ShowPage("Guided Setup");
    }

    private UIElement CompactWizardStep(int number, string title, string detail, UIElement action, WorkflowState completeState, WorkflowState unlockState)
    {
        var completed = HasReached(completeState);
        var current = !completed && HasReached(unlockState);
        var accent = completed ? AccentGreen : current ? AccentBlue : Secondary;
        var stateText = completed ? "Completed" : current ? "Current" : "Locked";

        var grid = new Grid
        {
            ColumnSpacing = 14,
            MinHeight = 58
        };
        grid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(44) });
        grid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(132) });
        grid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
        grid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(430) });

        grid.Children.Add(Badge(number.ToString(), accent));

        var titleBlock = Text(title, 14, SemiBoldWeight, White);
        titleBlock.TextTrimming = TextTrimming.CharacterEllipsis;
        titleBlock.TextWrapping = TextWrapping.NoWrap;
        SetGridColumn(titleBlock, 1);
        grid.Children.Add(titleBlock);

        var detailStack = Stack(StatusBadge(stateText, accent), Spaced(detail, 12, current ? White : Secondary));
        SetGridColumn(detailStack, 2);
        grid.Children.Add(detailStack);

        var actionHost = new Border
        {
            HorizontalAlignment = HorizontalAlignment.Stretch,
            Child = action
        };
        SetGridColumn(actionHost, 3);
        grid.Children.Add(actionHost);

        var panel = Panel(grid, current ? "#102033" : completed ? "#0E211C" : "#0C1219");
        panel.Padding = new Thickness(14, 9, 14, 9);
        panel.Margin = new Thickness(0, 7, 0, 0);
        panel.BorderBrush = current ? AccentBlue : completed ? Brush("#2A7356") : Brush("#18212C");
        return panel;
    }

    private UIElement WizardStep(int number, string title, string detail, UIElement action, WorkflowState completeState, WorkflowState unlockState)
    {
        var completed = HasReached(completeState);
        var current = !completed && HasReached(unlockState);
        var accent = completed ? AccentGreen : current ? AccentBlue : Secondary;
        var stateText = completed ? "Completed" : current ? "Current" : "Locked";

        var grid = new Grid { ColumnSpacing = 10 };
        grid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(34) });
        grid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
        grid.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });
        grid.Children.Add(Badge(number.ToString(), accent));

        var titleRow = new StackPanel { Orientation = Orientation.Horizontal, Spacing = 8 };
        titleRow.Children.Add(Text(title, 14, SemiBoldWeight, White));
        titleRow.Children.Add(StatusBadge(stateText, accent));

        var copy = Stack(
            titleRow,
            Spaced(detail, 11, current ? White : Secondary));
        Grid.SetColumn(copy, 1);
        grid.Children.Add(copy);

        SetGridColumn(action, 2);
        grid.Children.Add(action);

        var panel = Panel(grid, current ? "#102033" : completed ? "#0E211C" : "#0C1219");
        panel.Padding = new Thickness(12, 10, 12, 10);
        panel.Margin = new Thickness(0, 4, 0, 0);
        panel.BorderBrush = current ? AccentBlue : completed ? Brush("#2A7356") : Brush("#18212C");
        return panel;
    }

    private UIElement EmptyActionPage(string title, string detail, string buttonText, bool enabled, RoutedEventHandler click, IEnumerable<string>? checklist = null)
    {
        var button = PrimaryButton(buttonText, enabled ? AccentBlue : Brush("#243141"), click);
        button.IsEnabled = enabled;
        var stack = Stack(
            Text(title, 26, SemiBoldWeight, White),
            Spaced(detail, 15, Secondary),
            button,
            Spaced("Current state: " + WorkflowLabel(), 13, AccentBlue),
            Spaced("No files will be changed until you confirm a write action.", 13, AccentGreen));

        if (checklist != null)
        {
            foreach (var item in checklist)
            {
                stack.Children.Add(Spaced("- " + item, 13, Secondary));
            }
        }

        return Panel(stack);
    }

    private UIElement ManifestPanel()
    {
        var stack = Stack();
        stack.Children.Add(Text("Manifest list", 20, SemiBoldWeight, White));
        if (!HasReached(WorkflowState.Staged))
        {
            stack.Children.Add(ManifestRow("staging", "Staging", "Waiting for staging", "Apply to staging after plan review to create the first manifest."));
            return Panel(stack);
        }

        stack.Children.Add(ManifestRow("staging-latest", "Staging", "Created by staging", "Tracks files copied into the staging folder."));
        if (!HasReached(WorkflowState.RestoreAvailable))
        {
            stack.Children.Add(ManifestRow("game-apply", "Game", "Locked until confirmation", "Confirm game apply to create the game restore manifest."));
            return Panel(stack);
        }

        stack.Children.Add(ManifestRow("game-latest", "Game", "Available", "Tracks files written to the game folder and powers restore preview."));
        return Panel(stack);
    }

    private UIElement ProjectSummaryPanel()
    {
        return Panel(Stack(
            Text(HasReached(WorkflowState.ProjectOpened) ? "Wilds Project" : "No project open", 22, SemiBoldWeight, White),
            HasReached(WorkflowState.ProjectOpened)
                ? PathLine("Project file", @"D:\ModForge\Projects\Wilds Project\project.mfproj")
                : Spaced("Open a project to begin the safe workflow.", 12, Secondary),
            Line("Profile", HasReached(WorkflowState.ModFamilyChosen) ? selectedFamily : "Not selected", AccentBlue),
            Line("Enabled mods", HasReached(WorkflowState.Scanned) ? "16 / 24" : "Scan required", HasReached(WorkflowState.Scanned) ? AccentGreen : Secondary),
            Line("Apply to game", GameWriteLabel(), HasReached(WorkflowState.RestoreAvailable) ? AccentGreen : HasReached(WorkflowState.Staged) ? AccentAmber : Secondary)));
    }

    private UIElement NextActionCard()
    {
        return Panel(Stack(
            Text("Next safe action", 13, SemiBoldWeight, AccentGreen),
            Spaced(GetNextAction(), 16, White)), "#0E241C", "#2A7356");
    }

    private UIElement WorkflowStepper()
    {
        var grid = new Grid { ColumnSpacing = 8, Margin = new Thickness(0, 12, 16, 0) };
        for (var i = 0; i < 6; i++)
        {
            grid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
        }

        var steps = new[]
        {
            ("Project", WorkflowState.ProjectOpened),
            ("Family", WorkflowState.ModFamilyChosen),
            ("Folders", WorkflowState.ModsFolderSelected),
            ("Scan", WorkflowState.Scanned),
            ("Review", WorkflowState.PlanReviewed),
            ("Staged", WorkflowState.Staged)
        };

        for (var i = 0; i < steps.Length; i++)
        {
            var pill = Panel(Text(steps[i].Item1, 13, SemiBoldWeight, HasReached(steps[i].Item2) ? AccentGreen : Secondary), HasReached(steps[i].Item2) ? "#0E241C" : "#0F1721", HasReached(steps[i].Item2) ? "#2A7356" : "#243141");
            Grid.SetColumn(pill, i);
            grid.Children.Add(pill);
        }
        return grid;
    }

    private UIElement KpiRow()
    {
        return ButtonRow(Kpi("Total Mods", "24", AccentBlue), Kpi("Enabled", "16", AccentGreen), Kpi("Conflicts", "5", AccentRed), Kpi("Warnings", "3", AccentAmber));
    }

    private UIElement ModListRow(ModRow mod)
    {
        return RowGrid(new[]
        {
            mod.Enabled ? "On" : "Off",
            mod.Priority.ToString(),
            mod.Name,
            mod.Family,
            mod.Status,
            mod.Conflicts.ToString()
        }, mod.Conflicts > 0 ? AccentRed : AccentGreen);
    }

    private UIElement ConflictListRow(ConflictRow conflict)
    {
        return RowGrid(new[] { ShortPath(conflict.Destination, 46), conflict.WinningMod, conflict.LosingMod, conflict.Risk }, AccentAmber);
    }

    private UIElement ToolRow(string name, string state, string detail)
    {
        return RowGrid(new[] { name, state, detail }, state == "Idle" ? AccentGreen : Secondary);
    }

    private UIElement SelectedModPanel(ModRow mod)
    {
        return Stack(
            Text("Selected mod", 13, SemiBoldWeight, Secondary),
            Text(mod.Name, 22, SemiBoldWeight, White),
            Line("Family", mod.Family, AccentBlue),
            Line("Status", mod.Status, mod.Status == "OK" ? AccentGreen : AccentAmber),
            PathLine("Source path", mod.Source),
            PathLine("Destination", mod.Destination),
            Line("Conflicts", mod.Conflicts.ToString(), mod.Conflicts > 0 ? AccentRed : AccentGreen),
            Line("Warnings", mod.Warnings.ToString(), mod.Warnings > 0 ? AccentAmber : AccentGreen),
            SectionTitle("Safe action"),
            Spaced(mod.SafeAction, 13, White),
            ButtonRow(
                PrimaryButton("View conflicts", AccentAmber, (_, _) => ShowPage("Plan")),
                PrimaryButton("Disable mod", Secondary, (_, _) => SetStatus("Disable will be wired to the sidecar after scan integration."))));
    }

    private UIElement HeaderRow(IReadOnlyList<string> labels)
    {
        var row = RowGrid(labels, Secondary);
        row.Margin = new Thickness(0, 12, 0, 0);
        row.Background = Brush("#14202C");
        return row;
    }

    private Grid RowGrid(IReadOnlyList<string> values, Brush accent)
    {
        var grid = new Grid { ColumnSpacing = 12, Padding = new Thickness(12, 10, 12, 10), Background = Brush("#101821") };
        for (var i = 0; i < values.Count; i++)
        {
            grid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(i == 2 ? 1.5 : 1.0, GridUnitType.Star) });
            var text = Text(values[i], 13, SemiBoldWeight, i == values.Count - 1 ? accent : White);
            text.TextTrimming = TextTrimming.CharacterEllipsis;
            text.TextWrapping = TextWrapping.NoWrap;
            Grid.SetColumn(text, i);
            grid.Children.Add(text);
        }
        return grid;
    }

    private UIElement ManifestRow(string id, string target, string state, string summary)
    {
        return Panel(Stack(
            Text(id + " - " + target, 14, SemiBoldWeight, White),
            Spaced(state, 12, Secondary),
            Spaced(summary, 12, Secondary)), "#0F1721", "#243141");
    }

    private UIElement InfoPanel(string title, IEnumerable<string> lines)
    {
        var stack = Stack();
        stack.Children.Add(Text(title, 20, SemiBoldWeight, White));
        foreach (var line in lines)
        {
            stack.Children.Add(Spaced("- " + line, 13, Secondary));
        }
        return Panel(stack);
    }

    private UIElement Line(string label, string value, Brush brush)
    {
        var grid = new Grid { Margin = new Thickness(0, 12, 0, 0), ColumnSpacing = 12 };
        grid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(132) });
        grid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
        grid.Children.Add(Text(label, 13, NormalWeight, Secondary));
        var right = Text(value, 13, SemiBoldWeight, brush);
        Grid.SetColumn(right, 1);
        grid.Children.Add(right);
        return grid;
    }

    private UIElement PathLine(string label, string path)
    {
        var grid = new Grid { Margin = new Thickness(0, 12, 0, 0), ColumnSpacing = 12 };
        grid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(132) });
        grid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
        grid.Children.Add(Text(label, 13, NormalWeight, Secondary));
        var right = PathText(path);
        Grid.SetColumn(right, 1);
        grid.Children.Add(right);
        return grid;
    }

    private Button WizardButton(string content, bool enabled, RoutedEventHandler click)
    {
        var button = PrimaryButton(content, enabled ? AccentBlue : Brush("#243141"), click);
        button.IsEnabled = enabled;
        return button;
    }

    private Button PrimaryButton(string content, Brush accent, RoutedEventHandler click)
    {
        var button = new Button
        {
            Content = content,
            Margin = new Thickness(0, 0, 0, 0),
            Padding = new Thickness(13, 7, 13, 7),
            BorderBrush = accent,
            BorderThickness = new Thickness(1),
            Background = Brush("#111D2A"),
            Foreground = White
        };
        button.Click += click;
        return button;
    }

    private StackPanel ButtonRow(params UIElement[] elements)
    {
        var row = new StackPanel { Orientation = Orientation.Horizontal, Spacing = 8, Margin = new Thickness(0, 12, 0, 0) };
        foreach (var element in elements)
        {
            row.Children.Add(element);
        }
        return row;
    }

    private UIElement Kpi(string label, string value, Brush accent)
    {
        return Panel(Stack(Text(label, 11, NormalWeight, Secondary), Text(value, 20, SemiBoldWeight, accent)), "#0F1721", "#243141");
    }

    private TextBlock SectionTitle(string value)
    {
        var text = Text(value, 18, SemiBoldWeight, White);
        text.Margin = new Thickness(0, 16, 0, 0);
        return text;
    }

    private UIElement StatusBadge(string value, Brush accent)
    {
        return new Border
        {
            Padding = new Thickness(8, 3, 8, 4),
            CornerRadius = new CornerRadius(10),
            Background = Brush("#0F1721"),
            BorderBrush = accent,
            BorderThickness = new Thickness(1),
            Child = Text(value, 11, SemiBoldWeight, accent)
        };
    }

    private UIElement Badge(string value, Brush accent)
    {
        return new Border
        {
            Width = 28,
            Height = 28,
            CornerRadius = new CornerRadius(14),
            Background = accent,
            Child = new TextBlock
            {
                Text = value,
                FontSize = 12,
                FontWeight = BoldWeight,
                Foreground = White,
                HorizontalAlignment = HorizontalAlignment.Center,
                VerticalAlignment = VerticalAlignment.Center
            }
        };
    }

    private Border Panel(UIElement child, string background = "#111A24", string border = "#243141")
    {
        return new Border
        {
            Padding = new Thickness(16),
            Margin = new Thickness(0, 0, 0, 12),
            CornerRadius = new CornerRadius(12),
            Background = Brush(background),
            BorderBrush = Brush(border),
            BorderThickness = new Thickness(1),
            Child = child
        };
    }

    private StackPanel Stack(params UIElement[] children)
    {
        var stack = new StackPanel { Spacing = 0 };
        foreach (var child in children)
        {
            stack.Children.Add(child);
        }
        return stack;
    }

    private Grid TwoColumnGrid(double leftWeight, double rightWeight)
    {
        var grid = new Grid { ColumnSpacing = 16 };
        grid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(leftWeight, GridUnitType.Star) });
        grid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(rightWeight, GridUnitType.Star) });
        return grid;
    }

    private Grid TwoColumnGrid(double leftWeight, double rightWeight, UIElement left, UIElement right)
    {
        var grid = TwoColumnGrid(leftWeight, rightWeight);
        SetGridColumn(left, 0);
        SetGridColumn(right, 1);
        grid.Children.Add(left);
        grid.Children.Add(right);
        return grid;
    }

    private TextBlock Text(string value, double size, FontWeight weight, Brush brush)
    {
        return new TextBlock
        {
            Text = value,
            FontSize = size,
            FontWeight = weight,
            Foreground = brush,
            TextWrapping = TextWrapping.Wrap
        };
    }

    private TextBlock PathText(string value)
    {
        return new TextBlock
        {
            Text = value,
            FontSize = 12,
            FontWeight = SemiBoldWeight,
            Foreground = Secondary,
            FontFamily = new FontFamily("Cascadia Mono"),
            TextWrapping = TextWrapping.NoWrap,
            TextTrimming = TextTrimming.CharacterEllipsis
        };
    }

    private TextBlock Spaced(string value, double size, Brush brush)
    {
        var text = Text(value, size, NormalWeight, brush);
        text.Margin = new Thickness(0, 8, 0, 0);
        return text;
    }

    private void AdvanceState(WorkflowState state, string message)
    {
        if (state > workflowState)
        {
            workflowState = state;
        }
        SetStatus(message);
        UpdateShell();
    }

    private bool HasReached(WorkflowState state) => workflowState >= state;

    private bool CanScan() => HasReached(WorkflowState.ModsFolderSelected);

    private bool CanCreatePlan() => HasReached(WorkflowState.Scanned);

    private bool IsCurrentStep(WorkflowState completeState, WorkflowState unlockState) => !HasReached(completeState) && HasReached(unlockState);

    private bool CanApplyToStaging() => planReviewManuallyChecked && HasReached(WorkflowState.PlanReviewed) && !HasReached(WorkflowState.Staged);

    private string StagingActionLabel() => HasReached(WorkflowState.Staged) ? "Staging complete" : CanApplyToStaging() ? "Apply to staging" : "Apply to staging locked";

    private string GameWriteLabel()
    {
        if (HasReached(WorkflowState.RestoreAvailable)) return "Manifest available";
        if (HasReached(WorkflowState.Staged)) return "Confirmation required";
        return "Locked";
    }

    private string StepStateText(string label, WorkflowState state)
    {
        return label + ": " + (HasReached(state) ? "complete" : "required");
    }

    private static string ShortPath(string path, int maxLength)
    {
        if (path.Length <= maxLength)
        {
            return path;
        }

        var fileStart = path.LastIndexOf('\\');
        if (fileStart < 0)
        {
            return "..." + path.Substring(path.Length - Math.Min(path.Length, maxLength - 3));
        }

        var file = path.Substring(fileStart + 1);
        var prefixLength = Math.Max(6, maxLength - file.Length - 6);
        var prefix = path.Substring(0, Math.Min(prefixLength, path.Length));
        return prefix + @"\...\" + file;
    }

    private string WorkflowLabel()
    {
        return workflowState switch
        {
            WorkflowState.NoProject => "No project",
            WorkflowState.ProjectOpened => "Project opened",
            WorkflowState.ModFamilyChosen => "Mod family chosen",
            WorkflowState.GameFolderSelected => "Game folder selected",
            WorkflowState.ModsFolderSelected => "Mods folder selected",
            WorkflowState.Scanned => "Scan complete",
            WorkflowState.PlanReady => "Plan ready",
            WorkflowState.PlanReviewed => "Plan reviewed",
            WorkflowState.Staged => "Staged",
            WorkflowState.GameApplied => "Game applied",
            WorkflowState.RestoreAvailable => "Restore manifest available",
            _ => workflowState.ToString()
        };
    }

    private string GetNextAction()
    {
        return workflowState switch
        {
            WorkflowState.NoProject => "Open a project or start Guided Setup.",
            WorkflowState.ProjectOpened => "Choose a mod family.",
            WorkflowState.ModFamilyChosen => "Choose the game folder.",
            WorkflowState.GameFolderSelected => "Choose the mods folder.",
            WorkflowState.ModsFolderSelected => "Scan mods.",
            WorkflowState.Scanned => "Create and review the plan.",
            WorkflowState.PlanReady => "Review conflicts and warnings.",
            WorkflowState.PlanReviewed => "Apply to staging.",
            WorkflowState.Staged => "Open Apply & Restore and confirm game apply.",
            WorkflowState.RestoreAvailable => "Preview restore or inspect the latest manifest.",
            _ => "Preview restore or inspect the manifest."
        };
    }

    private void SetStatus(string message)
    {
        statusMessage = message;
        UpdateShell();
    }

    private void ConfigureWindowPersistence()
    {
        try
        {
            var hwnd = WinRT.Interop.WindowNative.GetWindowHandle(this);
            var windowId = Win32Interop.GetWindowIdFromWindow(hwnd);
            appWindow = AppWindow.GetFromWindowId(windowId);
            var initialSize = LoadWindowSize() ?? new SizeInt32(1480, 900);
            appWindow.Resize(initialSize);
            pendingWindowSize = initialSize;

            var dispatcherQueue = DispatcherQueue.GetForCurrentThread();
            windowSizeSaveTimer = dispatcherQueue.CreateTimer();
            windowSizeSaveTimer.Interval = TimeSpan.FromMilliseconds(450);
            windowSizeSaveTimer.Tick += (_, _) =>
            {
                windowSizeSaveTimer.Stop();
                SaveWindowSize(pendingWindowSize);
            };

            appWindow.Changed += (_, args) =>
            {
                if (!args.DidSizeChange || appWindow == null)
                {
                    return;
                }

                pendingWindowSize = appWindow.Size;
                windowSizeSaveTimer.Stop();
                windowSizeSaveTimer.Start();
            };

            Closed += (_, _) =>
            {
                if (appWindow != null)
                {
                    SaveWindowSize(appWindow.Size);
                }
            };
        }
        catch
        {
            // Window sizing is a convenience; layout still works if the host denies it.
        }
    }

    private static SizeInt32? LoadWindowSize()
    {
        try
        {
            var path = WindowSettingsPath();
            if (!File.Exists(path))
            {
                return null;
            }

            var settings = JsonSerializer.Deserialize<WindowSettings>(File.ReadAllText(path));
            if (settings == null || settings.Width < 1120 || settings.Height < 720)
            {
                return null;
            }

            return new SizeInt32(settings.Width, settings.Height);
        }
        catch
        {
            return null;
        }
    }

    private static void SaveWindowSize(SizeInt32 size)
    {
        if (size.Width < 1120 || size.Height < 720)
        {
            return;
        }

        try
        {
            var path = WindowSettingsPath();
            Directory.CreateDirectory(Path.GetDirectoryName(path)!);
            var settings = new WindowSettings { Width = size.Width, Height = size.Height };
            var json = JsonSerializer.Serialize(settings, new JsonSerializerOptions { WriteIndented = true });
            File.WriteAllText(path, json);
        }
        catch
        {
            // Persisting window size should never prevent the shell from running.
        }
    }

    private static string WindowSettingsPath()
    {
        var root = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
        return Path.Combine(root, "ModForgeManager", "winui-window.json");
    }

    private void UpdateShell()
    {
        SafetyChip.Text = "Safe mode: Dry-run first | No startup scan | Python idle";
        StateChip.Text = "State: " + WorkflowLabel();
        StatusText.Text = WorkflowLabel() + " - " + (string.IsNullOrWhiteSpace(statusMessage) ? GetNextAction() : statusMessage);

        ScanButton.IsEnabled = CanScan();
        PlanButton.IsEnabled = CanCreatePlan();
        ApplyButton.IsEnabled = HasReached(WorkflowState.Staged);
        ApplyButton.Content = HasReached(WorkflowState.RestoreAvailable)
            ? "Preview restore"
            : HasReached(WorkflowState.Staged)
                ? "Open game confirm"
                : "Apply to game locked";

        NavMods.Opacity = CanScan() || activePage == "Mods" ? 1.0 : 0.58;
        NavPlan.Opacity = CanCreatePlan() || activePage == "Plan" ? 1.0 : 0.58;
        NavApply.Opacity = HasReached(WorkflowState.PlanReady) || activePage == "Apply & Restore" ? 1.0 : 0.58;
    }

    private static List<ModRow> CreateMods()
    {
        return new List<ModRow>
        {
            new(true, 1, "Better UI", "REFramework", @"Mods\BetterUI", "OK", 0, 1, @"reframework\data\ui\betterui.lua", "Review conflict in Plan before staging."),
            new(true, 2, "Weapon Texture Pack", "Unreal Pak", "WeaponTX_Pack.zip", "OK", 1, 2, @"Content\Paks\~mods\WeaponTX_Pack.pak", "Keep archive intact and stage first."),
            new(true, 3, "REFramework Loader", "REFramework", @"Mods\REFramework", "OK", 0, 0, @"reframework\d2d\reframework.dll", "Ready for staging."),
            new(true, 4, "Unreal HD HUD", "Unreal Pak", "HDHUD_v2.zip", "Warn", 1, 1, @"Content\Paks\~mods\HDHUD_v2.pak", "Check warning before staging."),
            new(false, 5, "Monster Weakness Icon", "REFramework", @"Mods\WeaknessIcon", "Disabled", 0, 0, @"reframework\data\ui\icons.dds", "Enable only after conflict review."),
            new(true, 6, "STS2 Localization EN", "Godot PCK", "Localization_EN.pck", "OK", 0, 0, @"mods\Localization_EN.pck", "Ready for staging.")
        };
    }

    private static List<ConflictRow> CreateConflicts()
    {
        return new List<ConflictRow>
        {
            new(@"reframework\data\ui\betterui.lua", "Better UI", "Monster Weakness Icon", "Destination overwrite"),
            new(@"Content\Paks\~mods\WeaponTX_Pack.pak", "Weapon Texture Pack", "HD Monster Textures", "Archive destination"),
            new(@"reframework\data\ui\config.ini", "Better UI", "Unreal HD HUD", "Case-insensitive path match")
        };
    }

    private static List<string> CreateWarnings()
    {
        return new List<string>
        {
            "WeaponTX_Pack.zip has no preview image. This does not block staging.",
            "HDHUD_v2.zip duplicates one destination already used by another mod.",
            "Unreal sidecar archives must be restored as a set."
        };
    }

    private static SolidColorBrush Brush(string hex)
    {
        var value = hex.TrimStart('#');
        var r = Convert.ToByte(value.Substring(0, 2), 16);
        var g = Convert.ToByte(value.Substring(2, 2), 16);
        var b = Convert.ToByte(value.Substring(4, 2), 16);
        return new SolidColorBrush(Color.FromArgb(255, r, g, b));
    }

    private static SolidColorBrush AccentBlue => Brush("#4F9CFF");
    private static SolidColorBrush AccentGreen => Brush("#3ECF8E");
    private static SolidColorBrush AccentAmber => Brush("#F5B84B");
    private static SolidColorBrush AccentRed => Brush("#EF635B");
    private static SolidColorBrush Secondary => Brush("#9AA8B7");
    private static SolidColorBrush White => new(Colors.White);
    private static FontWeight NormalWeight => new() { Weight = 400 };
    private static FontWeight SemiBoldWeight => new() { Weight = 600 };
    private static FontWeight BoldWeight => new() { Weight = 700 };

    private static void SetGridColumn(UIElement element, int column)
    {
        if (element is FrameworkElement frameworkElement)
        {
            Grid.SetColumn(frameworkElement, column);
        }
    }

    private enum WorkflowState
    {
        NoProject = 0,
        ProjectOpened = 1,
        ModFamilyChosen = 2,
        GameFolderSelected = 3,
        ModsFolderSelected = 4,
        Scanned = 5,
        PlanReady = 6,
        PlanReviewed = 7,
        Staged = 8,
        GameApplied = 9,
        RestoreAvailable = 10
    }

    private sealed record ModRow(bool Enabled, int Priority, string Name, string Family, string Source, string Status, int Warnings, int Conflicts, string Destination, string SafeAction);

    private sealed record ConflictRow(string Destination, string WinningMod, string LosingMod, string Risk);

    private sealed class WindowSettings
    {
        public int Width { get; set; }

        public int Height { get; set; }
    }
}

