using System;
using System.Collections.Generic;
using System.Threading;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Controls.Primitives;
using System.Windows.Data;
using System.Windows.Media;

namespace ModForge.App
{
    public sealed class MainWindow : Window
    {
        private readonly IPythonSidecarService sidecar;
        private readonly StartupTelemetry telemetry;
        private readonly ProjectSnapshot snapshot;
        private readonly Dictionary<string, Button> navigationButtons;

        private WorkflowState workflowState;
        private string activePage;
        private string selectedFamily;
        private string statusMessage;
        private bool planReviewManuallyChecked;
        private bool gameApplyConfirmationChecked;

        private Grid contentGrid;
        private TextBlock pageTitle;
        private TextBlock pageSubtitle;
        private TextBlock statusText;
        private TextBlock telemetryText;
        private TextBlock safetyChipText;
        private TextBlock workflowChipText;
        private Button openProjectButton;
        private Button scanButton;
        private Button planButton;
        private Button applyButton;

        private readonly Brush appBackground = BrushFrom("#0A0F16");
        private readonly Brush sidebarBackground = BrushFrom("#0D141D");
        private readonly Brush panelBackground = BrushFrom("#111A24");
        private readonly Brush panelBackgroundSoft = BrushFrom("#0F1721");
        private readonly Brush panelBorder = BrushFrom("#243141");
        private readonly Brush textPrimary = BrushFrom("#EEF4FA");
        private readonly Brush textSecondary = BrushFrom("#9AA8B7");
        private readonly Brush accentBlue = BrushFrom("#4F9CFF");
        private readonly Brush accentGreen = BrushFrom("#3ECF8E");
        private readonly Brush accentAmber = BrushFrom("#F5B84B");
        private readonly Brush accentRed = BrushFrom("#EF635B");
        private readonly Brush accentPurple = BrushFrom("#C47CFF");

        public MainWindow(IPythonSidecarService sidecarService, StartupTelemetry startupTelemetry)
        {
            sidecar = sidecarService;
            telemetry = startupTelemetry;
            snapshot = sidecar.CreateInitialSnapshot();
            navigationButtons = new Dictionary<string, Button>();
            workflowState = WorkflowState.NoProject;
            activePage = "Home";
            selectedFamily = "Not selected";
            statusMessage = "Start Guided Setup to open a project safely.";

            Title = "ModForge Manager";
            Width = 1440;
            Height = 860;
            MinWidth = 1120;
            MinHeight = 720;
            Background = appBackground;
            WindowStartupLocation = WindowStartupLocation.CenterScreen;
            FontFamily = new FontFamily("Segoe UI");

            BuildShell();
            ShowPage("Home");
            UpdateWorkflowUi();
        }

        public void RefreshTelemetry()
        {
            if (telemetryText != null)
            {
                telemetryText.Text = telemetry.Summary();
            }
        }

        private void BuildShell()
        {
            var root = new Grid();
            root.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(232) });
            root.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
            Content = root;

            var sidebar = BuildSidebar();
            Grid.SetColumn(sidebar, 0);
            root.Children.Add(sidebar);

            var main = new Grid { Background = appBackground };
            main.RowDefinitions.Add(new RowDefinition { Height = new GridLength(82) });
            main.RowDefinitions.Add(new RowDefinition { Height = new GridLength(1, GridUnitType.Star) });
            main.RowDefinitions.Add(new RowDefinition { Height = new GridLength(36) });
            Grid.SetColumn(main, 1);
            root.Children.Add(main);

            var header = BuildHeader();
            Grid.SetRow(header, 0);
            main.Children.Add(header);

            contentGrid = new Grid { Margin = new Thickness(22, 18, 22, 18) };
            Grid.SetRow(contentGrid, 1);
            main.Children.Add(contentGrid);

            var footer = BuildFooter();
            Grid.SetRow(footer, 2);
            main.Children.Add(footer);
        }

        private UIElement BuildSidebar()
        {
            var border = new Border
            {
                Background = sidebarBackground,
                BorderBrush = panelBorder,
                BorderThickness = new Thickness(0, 0, 1, 0)
            };

            var layout = new DockPanel();
            border.Child = layout;

            var brand = new StackPanel { Margin = new Thickness(18, 18, 18, 22) };
            DockPanel.SetDock(brand, Dock.Top);
            layout.Children.Add(brand);

            var logoRow = new StackPanel { Orientation = Orientation.Horizontal };
            var logo = new Border
            {
                Width = 38,
                Height = 38,
                CornerRadius = new CornerRadius(10),
                Background = BrushFrom("#10233A"),
                BorderBrush = accentBlue,
                BorderThickness = new Thickness(1)
            };
            logo.Child = new TextBlock
            {
                Text = "M",
                FontSize = 22,
                FontWeight = FontWeights.Bold,
                Foreground = accentBlue,
                HorizontalAlignment = HorizontalAlignment.Center,
                VerticalAlignment = VerticalAlignment.Center
            };
            logoRow.Children.Add(logo);
            logoRow.Children.Add(new StackPanel
            {
                Margin = new Thickness(12, 0, 0, 0),
                Children =
                {
                    Text("ModForge", 18, FontWeights.SemiBold, textPrimary),
                    Text("Manager", 12, FontWeights.Normal, textSecondary)
                }
            });
            brand.Children.Add(logoRow);

            var nav = new StackPanel { Margin = new Thickness(10, 0, 10, 0) };
            layout.Children.Add(nav);

            AddNav(nav, "Home", "Next action");
            AddNav(nav, "Guided Setup", "Step-by-step");
            AddNav(nav, "Mods", "Scan results");
            AddNav(nav, "Plan", "Review before apply");
            AddNav(nav, "Apply & Restore", "Manifests");
            AddNav(nav, "Tools", "Tool status");

            return border;
        }

        private void AddNav(Panel parent, string title, string subtitle)
        {
            var button = new Button
            {
                Tag = title,
                HorizontalContentAlignment = HorizontalAlignment.Stretch,
                Margin = new Thickness(0, 3, 0, 3),
                Padding = new Thickness(12, 9, 12, 9),
                Background = Brushes.Transparent,
                BorderBrush = Brushes.Transparent,
                BorderThickness = new Thickness(1),
                Cursor = System.Windows.Input.Cursors.Hand
            };

            button.Content = new StackPanel
            {
                Children =
                {
                    Text(title, 14, FontWeights.SemiBold, textPrimary),
                    Text(subtitle, 11, FontWeights.Normal, textSecondary)
                }
            };
            button.Click += delegate { ShowPage(title); };

            navigationButtons[title] = button;
            parent.Children.Add(button);
        }

        private UIElement BuildHeader()
        {
            var header = new Border
            {
                Background = BrushFrom("#0C121A"),
                BorderBrush = panelBorder,
                BorderThickness = new Thickness(0, 0, 0, 1)
            };

            var grid = new Grid { Margin = new Thickness(22, 0, 22, 0) };
            grid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
            grid.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });
            header.Child = grid;

            var titleStack = new StackPanel { VerticalAlignment = VerticalAlignment.Center };
            pageTitle = Text("Home", 20, FontWeights.SemiBold, textPrimary);
            pageSubtitle = Text("Guided, dry-run-first mod management.", 12, FontWeights.Normal, textSecondary);
            titleStack.Children.Add(pageTitle);
            titleStack.Children.Add(pageSubtitle);
            Grid.SetColumn(titleStack, 0);
            grid.Children.Add(titleStack);

            var right = new StackPanel { VerticalAlignment = VerticalAlignment.Center };
            Grid.SetColumn(right, 1);
            grid.Children.Add(right);

            var chips = new StackPanel
            {
                Orientation = Orientation.Horizontal,
                HorizontalAlignment = HorizontalAlignment.Right,
                Margin = new Thickness(0, 0, 0, 8)
            };
            safetyChipText = Text("Safe mode: Dry-run first | No startup scan | Python idle", 12, FontWeights.SemiBold, accentGreen);
            chips.Children.Add(Chip(safetyChipText, "#0E241C", "#245A46"));
            workflowChipText = Text("State: No project", 12, FontWeights.SemiBold, accentBlue);
            chips.Children.Add(Chip(workflowChipText, "#10233A", "#25557D"));
            right.Children.Add(chips);

            var actions = new StackPanel
            {
                Orientation = Orientation.Horizontal,
                HorizontalAlignment = HorizontalAlignment.Right
            };
            openProjectButton = ActionButton("Open Project", accentBlue, delegate { AdvanceState(WorkflowState.ProjectOpened, "Project opened. Choose a mod family next."); ShowPage("Guided Setup"); });
            scanButton = ActionButton("Scan Mods", accentGreen, delegate { AdvanceState(WorkflowState.Scanned, "Scan complete. No files were changed."); ShowPage("Mods"); });
            planButton = ActionButton("Plan", accentAmber, delegate { AdvanceState(WorkflowState.PlanReady, "Plan is ready. Review conflicts before staging."); ShowPage("Plan"); });
            applyButton = ActionButton("Apply to game locked", accentRed, delegate { HandleTopApplyAction(); });
            actions.Children.Add(openProjectButton);
            actions.Children.Add(scanButton);
            actions.Children.Add(planButton);
            actions.Children.Add(applyButton);
            right.Children.Add(actions);

            return header;
        }

        private UIElement BuildFooter()
        {
            var footer = new Grid { Background = BrushFrom("#090E14") };
            footer.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
            footer.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });

            statusText = Text("", 12, FontWeights.Normal, textSecondary);
            statusText.Margin = new Thickness(22, 0, 0, 0);
            statusText.VerticalAlignment = VerticalAlignment.Center;
            footer.Children.Add(statusText);

            telemetryText = Text("", 11, FontWeights.Normal, textSecondary);
            telemetryText.Margin = new Thickness(0, 0, 22, 0);
            telemetryText.VerticalAlignment = VerticalAlignment.Center;
            Grid.SetColumn(telemetryText, 1);
            footer.Children.Add(telemetryText);

            return footer;
        }

        private Border Chip(TextBlock content, string background, string border)
        {
            return new Border
            {
                Margin = new Thickness(8, 0, 0, 0),
                Padding = new Thickness(10, 4, 10, 5),
                CornerRadius = new CornerRadius(12),
                Background = BrushFrom(background),
                BorderBrush = BrushFrom(border),
                BorderThickness = new Thickness(1),
                Child = content
            };
        }

        private void ShowPage(string page)
        {
            activePage = page;
            contentGrid.Children.Clear();
            UpdateNavigationState();

            if (page == "Home")
            {
                pageTitle.Text = "Home";
                pageSubtitle.Text = "Follow one safe action at a time.";
                BuildHome();
            }
            else if (page == "Guided Setup")
            {
                pageTitle.Text = "Guided Setup";
                pageSubtitle.Text = "Choose, scan, review, stage, then apply.";
                BuildGuidedSetup();
            }
            else if (page == "Mods")
            {
                pageTitle.Text = "Mods";
                pageSubtitle.Text = HasReached(WorkflowState.Scanned)
                    ? "Inspect scanned mods and selected-mod details."
                    : "No real scan has been run yet.";
                BuildMods();
            }
            else if (page == "Plan")
            {
                pageTitle.Text = "Plan";
                pageSubtitle.Text = "Review conflicts and warnings before staging.";
                BuildPlan();
            }
            else if (page == "Apply & Restore")
            {
                pageTitle.Text = "Apply & Restore";
                pageSubtitle.Text = "Stage first, then confirm game apply and restore options.";
                BuildApplyRestore();
            }
            else
            {
                pageTitle.Text = "Tools";
                pageSubtitle.Text = "Check external tools only when needed.";
                BuildTools();
            }

            UpdateWorkflowUi();
        }

        private void BuildHome()
        {
            var grid = TwoColumnGrid(1.6, 1.0);
            contentGrid.Children.Add(grid);

            var left = new StackPanel();
            Grid.SetColumn(left, 0);
            grid.Children.Add(left);

            var hero = SoftPanel();
            hero.Padding = new Thickness(24);
            hero.Child = new StackPanel
            {
                Children =
                {
                    Text("Start with Guided Setup", 30, FontWeights.SemiBold, textPrimary),
                    SpacedText("ModForge will not scan folders, run Python, or write files until you choose an action. The safest path is open project, scan, review plan, apply to staging, then confirm game apply.", 14, textSecondary),
                    LargePrimaryButton("Start Guided Setup", accentBlue, delegate { ShowPage("Guided Setup"); }),
                    NextActionPanel()
                }
            };
            left.Children.Add(hero);

            left.Children.Add(SectionTitle("Workflow progress"));
            left.Children.Add(WorkflowStepper());

            var right = new StackPanel();
            Grid.SetColumn(right, 1);
            grid.Children.Add(right);
            right.Children.Add(ProjectSummaryPanel());
            right.Children.Add(StartupRulesPanel());
        }

        private void BuildGuidedSetup()
        {
            var grid = TwoColumnGrid(1.25, 1.0);
            contentGrid.Children.Add(grid);

            var stepsPanel = SoftPanel();
            stepsPanel.Padding = new Thickness(22);
            Grid.SetColumn(stepsPanel, 0);
            grid.Children.Add(stepsPanel);

            var steps = new StackPanel();
            steps.Children.Add(Text("Interactive setup", 24, FontWeights.SemiBold, textPrimary));
            steps.Children.Add(SpacedText("Use the buttons below to move the workflow forward. Locked actions become available only after the safe prerequisites are complete.", 13, textSecondary));
            steps.Children.Add(WizardStep(1, "Choose mod family", "Pick the layout ModForge should explain first.", FamilyButtons(), WorkflowState.ModFamilyChosen, WorkflowState.NoProject));
            steps.Children.Add(WizardStep(2, "Select game folder", "Choose the game root. No writes happen while selecting.", WizardButton("Choose game folder", IsCurrentWizardStep(WorkflowState.GameFolderSelected, WorkflowState.ModFamilyChosen), delegate { AdvanceState(WorkflowState.GameFolderSelected, "Game folder selected."); ShowPage("Guided Setup"); }), WorkflowState.GameFolderSelected, WorkflowState.ModFamilyChosen));
            steps.Children.Add(WizardStep(3, "Select mods folder", "Choose the folder or archive collection to inspect.", WizardButton("Choose mods folder", IsCurrentWizardStep(WorkflowState.ModsFolderSelected, WorkflowState.GameFolderSelected), delegate { AdvanceState(WorkflowState.ModsFolderSelected, "Mods folder selected. Scan is now available."); ShowPage("Guided Setup"); }), WorkflowState.ModsFolderSelected, WorkflowState.GameFolderSelected));
            steps.Children.Add(WizardStep(4, "Scan mods", "Scan only starts when you press the button.", WizardButton("Scan now", IsCurrentWizardStep(WorkflowState.Scanned, WorkflowState.ModsFolderSelected), delegate { AdvanceState(WorkflowState.Scanned, "Scan complete. Review the Mods tab."); ShowPage("Mods"); }), WorkflowState.Scanned, WorkflowState.ModsFolderSelected));
            steps.Children.Add(WizardStep(5, "Review plan and conflicts", "Open the plan review and mark it complete before staging.", WizardButton("Open plan review", IsCurrentWizardStep(WorkflowState.PlanReady, WorkflowState.Scanned), delegate { AdvanceState(WorkflowState.PlanReady, "Plan is ready for review."); ShowPage("Plan"); }), WorkflowState.PlanReviewed, WorkflowState.Scanned));
            steps.Children.Add(WizardStep(6, "Apply to staging", "Staging is the first write step and does not touch the game folder.", WizardButton(HasReached(WorkflowState.Staged) ? "Staging complete" : "Apply to staging", CanApplyToStaging(), delegate { AdvanceState(WorkflowState.Staged, "Applied to staging. Game apply can now be confirmed."); ShowPage("Apply & Restore"); }), WorkflowState.Staged, WorkflowState.PlanReviewed));
            steps.Children.Add(WizardStep(7, "Apply to game", "Requires staging and confirmation first.", WizardButton(HasReached(WorkflowState.RestoreAvailable) ? "Restore ready" : "Open game apply", HasReached(WorkflowState.Staged) && !HasReached(WorkflowState.RestoreAvailable), delegate { ShowPage("Apply & Restore"); SetStatus("Confirm game apply from the Apply & Restore page."); }), WorkflowState.RestoreAvailable, WorkflowState.Staged));
            stepsPanel.Child = steps;

            var right = new StackPanel();
            Grid.SetColumn(right, 1);
            grid.Children.Add(right);
            right.Children.Add(SelectedWorkflowPanel());
            right.Children.Add(StartupRulesPanel());
        }

        private void BuildMods()
        {
            if (!HasReached(WorkflowState.Scanned))
            {
                BuildEmptyActionPage(
                    "No real scan has been run yet.",
                    "Press Scan Mods to inspect your selected mods folder. No files will be changed.",
                    "Scan Mods",
                    HasReached(WorkflowState.ModsFolderSelected),
                    delegate { AdvanceState(WorkflowState.Scanned, "Scan complete. Mod results are ready."); ShowPage("Mods"); });
                return;
            }

            var grid = TwoColumnGrid(1.9, 0.95);
            contentGrid.Children.Add(grid);

            var left = SoftPanel();
            left.Padding = new Thickness(18);
            Grid.SetColumn(left, 0);
            grid.Children.Add(left);

            var layout = new DockPanel();
            left.Child = layout;

            var top = new StackPanel { Orientation = Orientation.Horizontal, Margin = new Thickness(0, 0, 0, 14) };
            top.Children.Add(KpiPill("Total Mods", snapshot.TotalMods.ToString(), accentBlue));
            top.Children.Add(KpiPill("Enabled", snapshot.EnabledMods.ToString(), accentGreen));
            top.Children.Add(KpiPill("Conflicts", snapshot.ConflictCount.ToString(), accentRed));
            top.Children.Add(KpiPill("Warnings", snapshot.WarningCount.ToString(), accentAmber));
            DockPanel.SetDock(top, Dock.Top);
            layout.Children.Add(top);

            var table = CreateDataGrid();
            table.ItemsSource = snapshot.Mods;
            table.Columns.Add(CheckColumn("Enabled", "Enabled", 0.7));
            table.Columns.Add(TextColumn("Priority", "Priority", 0.7));
            table.Columns.Add(TextColumn("Mod Name", "Name", 2.0));
            table.Columns.Add(TextColumn("Family", "Type", 1.1));
            table.Columns.Add(TextColumn("Source", "Source", 1.6));
            table.Columns.Add(TextColumn("Status", "Status", 0.8));
            table.Columns.Add(TextColumn("Conflicts", "Conflicts", 0.8));
            table.Columns.Add(TextColumn("Warnings", "Warnings", 0.8));
            layout.Children.Add(table);

            var detail = SoftPanel();
            detail.Padding = new Thickness(18);
            Grid.SetColumn(detail, 1);
            grid.Children.Add(detail);

            Action<ModRow> renderDetail = delegate (ModRow mod)
            {
                detail.Child = SelectedModPanel(mod);
            };
            table.SelectionChanged += delegate
            {
                var mod = table.SelectedItem as ModRow;
                if (mod != null)
                {
                    renderDetail(mod);
                }
            };
            if (snapshot.Mods.Count > 0)
            {
                table.SelectedItem = snapshot.Mods[0];
                renderDetail(snapshot.Mods[0]);
            }
        }

        private void BuildPlan()
        {
            if (!HasReached(WorkflowState.PlanReady))
            {
                BuildEmptyActionPage(
                    "No plan has been generated yet.",
                    "Run Scan Mods first, then open Plan to review conflicts and warnings before staging.",
                    "Create plan",
                    HasReached(WorkflowState.Scanned),
                    delegate { AdvanceState(WorkflowState.PlanReady, "Plan is ready. Review required."); ShowPage("Plan"); });
                return;
            }

            var grid = TwoColumnGrid(1.5, 1.0);
            contentGrid.Children.Add(grid);

            var left = new StackPanel();
            Grid.SetColumn(left, 0);
            grid.Children.Add(left);

            var summary = SoftPanel();
            summary.Padding = new Thickness(18);
            summary.Child = new StackPanel
            {
                Children =
                {
                    Text("Plan Summary", 22, FontWeights.SemiBold, textPrimary),
                    PlanLine("Copy to staging", "1,842 files", accentGreen),
                    PlanLine("Destination conflicts", "5 conflicts affecting 4 mods", accentRed),
                    PlanLine("Warnings", "3 review items", accentAmber)
                }
            };
            left.Children.Add(summary);

            left.Children.Add(SectionTitle("Conflict list"));
            var conflictGrid = CreateDataGrid();
            conflictGrid.Height = 240;
            conflictGrid.ItemsSource = snapshot.Conflicts;
            conflictGrid.Columns.Add(TextColumn("Destination", "Destination", 2.0));
            conflictGrid.Columns.Add(TextColumn("Winning Mod", "WinningMod", 1.1));
            conflictGrid.Columns.Add(TextColumn("Losing Mod", "LosingMod", 1.1));
            conflictGrid.Columns.Add(TextColumn("Risk", "Risk", 1.1));
            left.Children.Add(conflictGrid);

            var right = new StackPanel();
            Grid.SetColumn(right, 1);
            grid.Children.Add(right);

            var warnings = SoftPanel();
            warnings.Padding = new Thickness(18);
            var warningStack = new StackPanel();
            warningStack.Children.Add(Text("Warnings", 20, FontWeights.SemiBold, textPrimary));
            foreach (var warning in snapshot.Warnings)
            {
                warningStack.Children.Add(BulletLine(warning, accentAmber));
            }
            warnings.Child = warningStack;
            right.Children.Add(warnings);

            var review = SoftPanel();
            review.Padding = new Thickness(18);
            review.Margin = new Thickness(0, 16, 0, 0);
            var reviewStack = new StackPanel();
            reviewStack.Children.Add(Text("Review gate", 20, FontWeights.SemiBold, textPrimary));
            reviewStack.Children.Add(SpacedText("Apply to staging unlocks only after you confirm that conflicts and warnings were reviewed.", 13, textSecondary));
            var checkbox = new CheckBox
            {
                Content = "I reviewed the conflict and warning lists",
                Foreground = textPrimary,
                Margin = new Thickness(0, 14, 0, 12),
                IsChecked = planReviewManuallyChecked,
                IsEnabled = !planReviewManuallyChecked && !HasReached(WorkflowState.Staged)
            };
            var staging = ActionButton(StagingActionLabel(), accentGreen, delegate { AdvanceState(WorkflowState.Staged, "Applied to staging. Game apply is now available."); ShowPage("Apply & Restore"); });
            SetButtonState(staging, CanApplyToStaging());
            checkbox.Checked += delegate
            {
                planReviewManuallyChecked = true;
                AdvanceState(WorkflowState.PlanReviewed, "Plan review complete. Apply to staging is unlocked.");
                checkbox.IsEnabled = false;
                staging.Content = StagingActionLabel();
                SetButtonState(staging, CanApplyToStaging());
            };
            reviewStack.Children.Add(checkbox);
            reviewStack.Children.Add(staging);
            review.Child = reviewStack;
            right.Children.Add(review);
        }

        private void BuildApplyRestore()
        {
            var grid = TwoColumnGrid(1.1, 1.0);
            contentGrid.Children.Add(grid);

            var left = new StackPanel();
            Grid.SetColumn(left, 0);
            grid.Children.Add(left);

            var stagingPanel = SoftPanel();
            stagingPanel.Padding = new Thickness(18);
            var stagingStack = new StackPanel();
            stagingStack.Children.Add(Text("Staging actions", 22, FontWeights.SemiBold, textPrimary));
            stagingStack.Children.Add(SpacedText("Staging writes to the configured staging folder first. It does not touch the game folder.", 13, textSecondary));
            var applyToStaging = ActionButton(StagingActionLabel(), accentGreen, delegate { AdvanceState(WorkflowState.Staged, "Applied to staging. Game apply now requires explicit confirmation."); ShowPage("Apply & Restore"); });
            SetButtonState(applyToStaging, CanApplyToStaging());
            var openStaging = ActionButton("Open staging folder", accentBlue, delegate { SetStatus("Staging folder can be opened after staging is complete."); });
            SetButtonState(openStaging, HasReached(WorkflowState.Staged));
            stagingStack.Children.Add(RowActions(applyToStaging, openStaging));
            left.Children.Add(stagingPanel);
            stagingPanel.Child = stagingStack;

            var gamePanel = SoftPanel();
            gamePanel.Padding = new Thickness(18);
            gamePanel.Margin = new Thickness(0, 16, 0, 0);
            gamePanel.BorderBrush = HasReached(WorkflowState.Staged) ? accentRed : panelBorder;
            var gameStack = new StackPanel();
            gameStack.Children.Add(Text(HasReached(WorkflowState.RestoreAvailable) ? "Restore manifest available" : "Game apply confirm zone", 22, FontWeights.SemiBold, HasReached(WorkflowState.Staged) ? accentRed : textPrimary));
            if (!HasReached(WorkflowState.Staged))
            {
                gameStack.Children.Add(SpacedText("Game apply stays locked until a staging manifest exists.", 13, textSecondary));
                var lockedApply = ActionButton("Confirm game apply locked", panelBorder, delegate { SetStatus("Apply to staging first, then confirm game apply."); });
                SetButtonState(lockedApply, false);
                gameStack.Children.Add(RowActions(lockedApply));
            }
            else if (HasReached(WorkflowState.RestoreAvailable))
            {
                gameStack.Children.Add(SpacedText("Game apply is complete. The safest next step is to inspect the manifest or preview restore.", 13, textSecondary));
                gameStack.Children.Add(RowActions(
                    ActionButton("View latest manifest", accentBlue, delegate { SetStatus("Latest manifest is ready for inspection."); }),
                    ActionButton("Preview restore", accentGreen, delegate { SetStatus("Restore preview is ready."); })));
            }
            else
            {
                gameStack.Children.Add(SpacedText("This action writes to the game folder. Confirm explicitly before the button unlocks.", 13, textSecondary));
                var confirmCheck = new CheckBox
                {
                    Content = "I understand this writes staged files to the game folder",
                    Foreground = textPrimary,
                    Margin = new Thickness(0, 14, 0, 12),
                    IsChecked = gameApplyConfirmationChecked
                };
                var confirmApply = ActionButton("Confirm game apply", accentRed, delegate { AdvanceState(WorkflowState.RestoreAvailable, "Game apply complete. Restore manifest is available."); ShowPage("Apply & Restore"); });
                SetButtonState(confirmApply, gameApplyConfirmationChecked);
                confirmCheck.Checked += delegate
                {
                    gameApplyConfirmationChecked = true;
                    SetButtonState(confirmApply, true);
                    SetStatus("Explicit confirmation received. Confirm game apply is unlocked.");
                };
                confirmCheck.Unchecked += delegate
                {
                    gameApplyConfirmationChecked = false;
                    SetButtonState(confirmApply, false);
                    SetStatus("Confirm game apply is locked until the confirmation box is checked.");
                };
                gameStack.Children.Add(confirmCheck);
                gameStack.Children.Add(RowActions(confirmApply, ActionButton("View staging manifest", accentBlue, delegate { SetStatus("Staging manifest is ready for inspection."); })));
            }
            gamePanel.Child = gameStack;
            left.Children.Add(gamePanel);

            var right = new StackPanel();
            Grid.SetColumn(right, 1);
            grid.Children.Add(right);

            var manifestPanel = SoftPanel();
            manifestPanel.Padding = new Thickness(18);
            manifestPanel.Child = ManifestListPanel();
            right.Children.Add(manifestPanel);

            var restorePanel = SoftPanel();
            restorePanel.Padding = new Thickness(18);
            restorePanel.Margin = new Thickness(0, 16, 0, 0);
            var previewRestore = ActionButton("Preview restore", accentBlue, delegate { SetStatus("Restore preview opened."); });
            var restoreSelected = ActionButton("Restore selected files", accentAmber, delegate { SetStatus("Selected restore requires a manifest selection."); });
            var restoreAll = ActionButton("Restore all from latest", accentRed, delegate { SetStatus("Full restore stays behind a confirmation dialog."); });
            SetButtonState(previewRestore, HasReached(WorkflowState.RestoreAvailable));
            SetButtonState(restoreSelected, HasReached(WorkflowState.RestoreAvailable));
            SetButtonState(restoreAll, HasReached(WorkflowState.RestoreAvailable));
            restorePanel.Child = new StackPanel
            {
                Children =
                {
                    Text("Restore actions", 20, FontWeights.SemiBold, textPrimary),
                    SpacedText("Restore remains manifest-bound. Preview before restoring selected files or a full manifest.", 13, textSecondary),
                    RowActions(previewRestore, restoreSelected, restoreAll)
                }
            };
            right.Children.Add(restorePanel);

            UpdateWorkflowUi();
        }

        private void BuildTools()
        {
            var grid = TwoColumnGrid(1.4, 1.0);
            contentGrid.Children.Add(grid);

            var left = SoftPanel();
            left.Padding = new Thickness(18);
            Grid.SetColumn(left, 0);
            grid.Children.Add(left);

            var toolTable = CreateDataGrid();
            toolTable.ItemsSource = snapshot.Tools;
            toolTable.Columns.Add(TextColumn("Tool", "Name", 0.9));
            toolTable.Columns.Add(TextColumn("Status", "Status", 0.8));
            toolTable.Columns.Add(TextColumn("Detail", "Detail", 2.4));
            left.Child = toolTable;

            var right = SoftPanel();
            right.Padding = new Thickness(18);
            Grid.SetColumn(right, 1);
            grid.Children.Add(right);

            var probeResult = Text("Python sidecar is idle.", 13, FontWeights.Normal, textSecondary);
            probeResult.Margin = new Thickness(0, 14, 0, 12);
            right.Child = new StackPanel
            {
                Children =
                {
                    Text("Tool checks", 22, FontWeights.SemiBold, textPrimary),
                    SpacedText("Tool checks are optional and run only when you request them.", 13, textSecondary),
                    probeResult,
                    ActionButton("Check Python Sidecar", accentBlue, async delegate
                    {
                        SetStatus("Checking Python sidecar...");
                        var result = await sidecar.ProbeAsync(CancellationToken.None);
                        probeResult.Text = result.Message;
                        probeResult.Foreground = result.Ok ? accentGreen : accentRed;
                        SetStatus(result.Title + ". " + result.Message);
                        UpdateWorkflowUi();
                    })
                }
            };
        }

        private void BuildEmptyActionPage(string title, string detail, string buttonText, bool enabled, RoutedEventHandler click)
        {
            var panel = SoftPanel();
            panel.Padding = new Thickness(28);
            panel.HorizontalAlignment = HorizontalAlignment.Stretch;
            panel.VerticalAlignment = VerticalAlignment.Top;
            contentGrid.Children.Add(panel);

            var button = LargePrimaryButton(buttonText, enabled ? accentBlue : panelBorder, click);
            button.IsEnabled = enabled;
            button.Opacity = enabled ? 1.0 : 0.45;
            panel.Child = new StackPanel
            {
                Children =
                {
                    Text(title, 26, FontWeights.SemiBold, textPrimary),
                    SpacedText(detail, 15, textSecondary),
                    button,
                    SpacedText("No files will be changed until you confirm a write action.", 13, accentGreen)
                }
            };
        }

        private UIElement FamilyButtons()
        {
            var row = new StackPanel { Orientation = Orientation.Horizontal, Margin = new Thickness(0, 10, 0, 0) };
            row.Children.Add(WizardButton("REFramework", true, delegate { SelectFamily("REFramework"); }));
            row.Children.Add(WizardButton("Unreal ~mods", true, delegate { SelectFamily("Unreal Mods"); }));
            row.Children.Add(WizardButton("Godot / STS2", true, delegate { SelectFamily("Godot / STS2"); }));
            return row;
        }

        private void SelectFamily(string family)
        {
            selectedFamily = family;
            AdvanceState(WorkflowState.ModFamilyChosen, family + " workflow selected. Choose the game folder next.");
            ShowPage("Guided Setup");
        }

        private UIElement WizardStep(int number, string title, string detail, UIElement action, WorkflowState completeState, WorkflowState unlockState)
        {
            var completed = HasReached(completeState);
            var current = !completed && HasReached(unlockState);
            var locked = !completed && !current;
            var accent = completed ? accentGreen : current ? accentBlue : textSecondary;
            var status = completed ? "Completed" : current ? "Current" : "Locked";
            var row = new Border
            {
                Margin = new Thickness(0, 12, 0, 0),
                Padding = new Thickness(14),
                Background = locked ? BrushFrom("#0C1219") : BrushFrom("#101C28"),
                BorderBrush = current ? accentBlue : completed ? BrushFrom("#2A7356") : BrushFrom("#18212C"),
                BorderThickness = new Thickness(1),
                CornerRadius = new CornerRadius(10)
            };
            var grid = new Grid();
            grid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(38) });
            grid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
            grid.ColumnDefinitions.Add(new ColumnDefinition { Width = GridLength.Auto });
            row.Child = grid;

            var badge = new Border
            {
                Width = 28,
                Height = 28,
                CornerRadius = new CornerRadius(14),
                Background = completed ? accentGreen : current ? accentBlue : BrushFrom("#1B2A39"),
                HorizontalAlignment = HorizontalAlignment.Left,
                VerticalAlignment = VerticalAlignment.Top
            };
            badge.Child = new TextBlock
            {
                Text = number.ToString(),
                FontSize = 12,
                FontWeight = FontWeights.Bold,
                Foreground = textPrimary,
                HorizontalAlignment = HorizontalAlignment.Center,
                VerticalAlignment = VerticalAlignment.Center
            };
            grid.Children.Add(badge);

            var copy = new StackPanel();
            copy.Children.Add(Text(title, 15, FontWeights.SemiBold, textPrimary));
            copy.Children.Add(SpacedText(detail, 12, textSecondary));
            copy.Children.Add(Text(status, 11, FontWeights.SemiBold, accent));
            Grid.SetColumn(copy, 1);
            grid.Children.Add(copy);

            Grid.SetColumn(action, 2);
            grid.Children.Add(action);
            return row;
        }

        private Button WizardButton(string text, bool enabled, RoutedEventHandler handler)
        {
            var button = ActionButton(text, enabled ? accentBlue : panelBorder, handler);
            button.Margin = new Thickness(8, 0, 0, 0);
            button.IsEnabled = enabled;
            button.Opacity = enabled ? 1.0 : 0.45;
            return button;
        }

        private Button LargePrimaryButton(string text, Brush accent, RoutedEventHandler handler)
        {
            var button = ActionButton(text, accent, handler);
            button.Margin = new Thickness(0, 22, 0, 0);
            button.Padding = new Thickness(18, 12, 18, 12);
            button.FontSize = 15;
            button.FontWeight = FontWeights.SemiBold;
            button.HorizontalAlignment = HorizontalAlignment.Left;
            return button;
        }

        private Border NextActionPanel()
        {
            var panel = new Border
            {
                Margin = new Thickness(0, 22, 0, 0),
                Padding = new Thickness(18),
                CornerRadius = new CornerRadius(14),
                Background = BrushFrom("#0E241C"),
                BorderBrush = BrushFrom("#2A7356"),
                BorderThickness = new Thickness(1)
            };
            panel.Child = new StackPanel
            {
                Children =
                {
                    Text("Next safe action", 13, FontWeights.SemiBold, accentGreen),
                    SpacedText(GetNextAction(), 16, textPrimary)
                }
            };
            return panel;
        }

        private Border SelectedWorkflowPanel()
        {
            var panel = SoftPanel();
            panel.Padding = new Thickness(20);
            panel.Margin = new Thickness(0, 0, 0, 16);
            panel.Child = new StackPanel
            {
                Children =
                {
                    Text("Selected workflow", 20, FontWeights.SemiBold, textPrimary),
                    PlanLine("Family", selectedFamily, selectedFamily == "Not selected" ? textSecondary : accentGreen),
                    PlanLine("State", WorkflowLabel(), accentBlue),
                    PlanLine("Game writes", GameWriteLabel(), HasReached(WorkflowState.RestoreAvailable) ? accentGreen : HasReached(WorkflowState.Staged) ? accentAmber : textSecondary)
                }
            };
            return panel;
        }

        private Border ProjectSummaryPanel()
        {
            var panel = SoftPanel();
            panel.Padding = new Thickness(20);
            panel.Margin = new Thickness(0, 0, 0, 16);
            panel.Child = new StackPanel
            {
                Children =
                {
                    Text(HasReached(WorkflowState.ProjectOpened) ? snapshot.ProjectName : "No project open", 22, FontWeights.SemiBold, textPrimary),
                    SpacedText(HasReached(WorkflowState.ProjectOpened) ? snapshot.ProjectPath : "Open a project to begin the safe workflow.", 12, textSecondary),
                    PlanLine("Profile", HasReached(WorkflowState.ModFamilyChosen) ? selectedFamily : "Not selected", accentBlue),
                    PlanLine("Enabled mods", HasReached(WorkflowState.Scanned) ? snapshot.EnabledMods + " / " + snapshot.TotalMods : "Scan required", HasReached(WorkflowState.Scanned) ? accentGreen : textSecondary),
                    PlanLine("Apply to game", GameWriteLabel(), HasReached(WorkflowState.RestoreAvailable) ? accentGreen : HasReached(WorkflowState.Staged) ? accentAmber : textSecondary)
                }
            };
            return panel;
        }

        private Border StartupRulesPanel()
        {
            var panel = SoftPanel();
            panel.Padding = new Thickness(20);
            panel.Child = new StackPanel
            {
                Children =
                {
                    Text("Safe startup", 18, FontWeights.SemiBold, textPrimary),
                    SpacedText("No startup scan.", 13, textSecondary),
                    SpacedText("No startup Python probe.", 13, textSecondary),
                    SpacedText("No external tool check until requested.", 13, textSecondary),
                    SpacedText("Write actions stay locked behind the workflow.", 13, accentGreen)
                }
            };
            return panel;
        }

        private UIElement WorkflowStepper()
        {
            var row = new UniformGrid { Columns = 6, Margin = new Thickness(0, 12, 16, 0) };
            row.Children.Add(StepPill("Project", WorkflowState.ProjectOpened));
            row.Children.Add(StepPill("Family", WorkflowState.ModFamilyChosen));
            row.Children.Add(StepPill("Folders", WorkflowState.ModsFolderSelected));
            row.Children.Add(StepPill("Scan", WorkflowState.Scanned));
            row.Children.Add(StepPill("Review", WorkflowState.PlanReviewed));
            row.Children.Add(StepPill("Staged", WorkflowState.Staged));
            return row;
        }

        private Border StepPill(string label, WorkflowState state)
        {
            var done = HasReached(state);
            var panel = new Border
            {
                Margin = new Thickness(0, 0, 8, 0),
                Padding = new Thickness(12, 10, 12, 10),
                CornerRadius = new CornerRadius(12),
                Background = done ? BrushFrom("#0E241C") : panelBackgroundSoft,
                BorderBrush = done ? BrushFrom("#2A7356") : panelBorder,
                BorderThickness = new Thickness(1)
            };
            panel.Child = Text(label, 13, FontWeights.SemiBold, done ? accentGreen : textSecondary);
            return panel;
        }

        private UIElement SelectedModPanel(ModRow mod)
        {
            if (mod == null)
            {
                return Text("Select a mod to inspect details.", 14, FontWeights.Normal, textSecondary);
            }

            return new StackPanel
            {
                Children =
                {
                    Text("Selected mod", 13, FontWeights.SemiBold, textSecondary),
                    Text(mod.Name, 22, FontWeights.SemiBold, textPrimary),
                    PlanLine("Family", mod.Type, accentBlue),
                    PlanLine("Status", mod.Status, mod.Status == "OK" ? accentGreen : accentAmber),
                    PlanLine("Source path", mod.Source, textSecondary),
                    PlanLine("Destination", mod.DestinationPaths, textSecondary),
                    PlanLine("Conflicts", mod.Conflicts.ToString(), mod.Conflicts > 0 ? accentRed : accentGreen),
                    PlanLine("Warnings", mod.Warnings.ToString(), mod.Warnings > 0 ? accentAmber : accentGreen),
                    SectionTitle("Safe action"),
                    SpacedText(mod.SafeAction, 13, textPrimary),
                    RowActions(
                        ActionButton("View conflicts", accentAmber, delegate { ShowPage("Plan"); }),
                        ActionButton("Disable mod", textSecondary, delegate { SetStatus("Disable will be wired to the sidecar after scan integration."); }))
                }
            };
        }

        private UIElement ManifestListPanel()
        {
            var stack = new StackPanel();
            stack.Children.Add(Text("Manifest list", 20, FontWeights.SemiBold, textPrimary));
            if (!HasReached(WorkflowState.Staged))
            {
                stack.Children.Add(ManifestRowPanel("staging", "Staging", "Waiting for staging", "Apply to staging after plan review to create the first manifest."));
                return stack;
            }

            stack.Children.Add(ManifestRowPanel("staging-latest", "Staging", "Created by staging", "Tracks files copied into the staging folder."));

            if (!HasReached(WorkflowState.RestoreAvailable))
            {
                stack.Children.Add(ManifestRowPanel("game-apply", "Game", "Locked until confirmation", "Confirm game apply to create the game restore manifest."));
                return stack;
            }

            stack.Children.Add(ManifestRowPanel("game-latest", "Game", "Available", "Tracks files written to the game folder and powers restore preview."));
            return stack;
        }

        private UIElement ManifestRowPanel(string id, string target, string state, string summary)
        {
            var row = new Border
            {
                Margin = new Thickness(0, 12, 0, 0),
                Padding = new Thickness(12),
                CornerRadius = new CornerRadius(10),
                Background = panelBackgroundSoft,
                BorderBrush = panelBorder,
                BorderThickness = new Thickness(1)
            };
            row.Child = new StackPanel
            {
                Children =
                {
                    Text(id + " - " + target, 14, FontWeights.SemiBold, textPrimary),
                    SpacedText(state, 12, textSecondary),
                    SpacedText(summary, 12, textSecondary)
                }
            };
            return row;
        }

        private UIElement RowActions(params Button[] buttons)
        {
            var row = new StackPanel { Orientation = Orientation.Horizontal, Margin = new Thickness(0, 16, 0, 0) };
            foreach (var button in buttons)
            {
                row.Children.Add(button);
            }
            return row;
        }

        private TextBlock BulletLine(string text, Brush accent)
        {
            return SpacedText("- " + text, 13, accent);
        }

        private Border KpiPill(string label, string value, Brush accent)
        {
            var panel = new Border
            {
                Margin = new Thickness(0, 0, 10, 0),
                Padding = new Thickness(14, 10, 14, 10),
                CornerRadius = new CornerRadius(12),
                Background = panelBackgroundSoft,
                BorderBrush = panelBorder,
                BorderThickness = new Thickness(1)
            };
            panel.Child = new StackPanel
            {
                Children =
                {
                    Text(label, 11, FontWeights.Normal, textSecondary),
                    Text(value, 20, FontWeights.SemiBold, accent)
                }
            };
            return panel;
        }

        private UIElement PlanLine(string label, string value, Brush accent)
        {
            var row = new Grid { Margin = new Thickness(0, 14, 0, 0) };
            row.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(132) });
            row.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(1, GridUnitType.Star) });
            row.Children.Add(Text(label, 13, FontWeights.Normal, textSecondary));
            var right = Text(value, 13, FontWeights.SemiBold, accent);
            Grid.SetColumn(right, 1);
            row.Children.Add(right);
            return row;
        }

        private DataGrid CreateDataGrid()
        {
            var headerStyle = new Style(typeof(DataGridColumnHeader));
            headerStyle.Setters.Add(new Setter(Control.BackgroundProperty, BrushFrom("#14202C")));
            headerStyle.Setters.Add(new Setter(Control.ForegroundProperty, textPrimary));
            headerStyle.Setters.Add(new Setter(Control.FontWeightProperty, FontWeights.SemiBold));
            headerStyle.Setters.Add(new Setter(Control.PaddingProperty, new Thickness(10, 8, 10, 8)));
            headerStyle.Setters.Add(new Setter(Control.BorderBrushProperty, panelBorder));
            headerStyle.Setters.Add(new Setter(Control.BorderThicknessProperty, new Thickness(0, 0, 1, 1)));

            var cellStyle = new Style(typeof(DataGridCell));
            cellStyle.Setters.Add(new Setter(Control.PaddingProperty, new Thickness(10, 6, 10, 6)));
            cellStyle.Setters.Add(new Setter(Control.BackgroundProperty, Brushes.Transparent));
            cellStyle.Setters.Add(new Setter(Control.ForegroundProperty, textPrimary));
            cellStyle.Setters.Add(new Setter(Control.BorderBrushProperty, BrushFrom("#1B2B3A")));

            var rowStyle = new Style(typeof(DataGridRow));
            rowStyle.Setters.Add(new Setter(Control.MinHeightProperty, 34.0));
            rowStyle.Setters.Add(new Setter(Control.BackgroundProperty, BrushFrom("#101821")));
            rowStyle.Setters.Add(new Setter(Control.ForegroundProperty, textPrimary));

            return new DataGrid
            {
                AutoGenerateColumns = false,
                IsReadOnly = true,
                Background = panelBackgroundSoft,
                Foreground = textPrimary,
                BorderBrush = panelBorder,
                GridLinesVisibility = DataGridGridLinesVisibility.Horizontal,
                HeadersVisibility = DataGridHeadersVisibility.Column,
                RowBackground = BrushFrom("#101821"),
                AlternatingRowBackground = BrushFrom("#0D151E"),
                HorizontalGridLinesBrush = panelBorder,
                VerticalGridLinesBrush = Brushes.Transparent,
                CanUserAddRows = false,
                CanUserDeleteRows = false,
                ColumnHeaderStyle = headerStyle,
                CellStyle = cellStyle,
                RowStyle = rowStyle,
                SelectionMode = DataGridSelectionMode.Single,
                SelectionUnit = DataGridSelectionUnit.FullRow,
                HorizontalScrollBarVisibility = ScrollBarVisibility.Disabled,
                VerticalScrollBarVisibility = ScrollBarVisibility.Auto
            };
        }

        private DataGridTextColumn TextColumn(string header, string binding, double width)
        {
            return new DataGridTextColumn
            {
                Header = header,
                Binding = new Binding(binding),
                Width = ColumnWidth(width)
            };
        }

        private DataGridCheckBoxColumn CheckColumn(string header, string binding, double width)
        {
            return new DataGridCheckBoxColumn
            {
                Header = header,
                Binding = new Binding(binding),
                Width = ColumnWidth(width)
            };
        }

        private DataGridLength ColumnWidth(double width)
        {
            if (width <= 10)
            {
                return new DataGridLength(width, DataGridLengthUnitType.Star);
            }
            return new DataGridLength(width);
        }

        private Grid TwoColumnGrid(double leftWeight, double rightWeight)
        {
            var grid = new Grid();
            grid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(leftWeight, GridUnitType.Star) });
            grid.ColumnDefinitions.Add(new ColumnDefinition { Width = new GridLength(rightWeight, GridUnitType.Star) });
            return grid;
        }

        private TextBlock SectionTitle(string text)
        {
            var title = Text(text, 18, FontWeights.SemiBold, textPrimary);
            title.Margin = new Thickness(0, 22, 0, 0);
            return title;
        }

        private Border SoftPanel()
        {
            return new Border
            {
                Background = panelBackground,
                BorderBrush = panelBorder,
                BorderThickness = new Thickness(1),
                CornerRadius = new CornerRadius(12)
            };
        }

        private Button ActionButton(string text, Brush accent, RoutedEventHandler handler)
        {
            var button = new Button
            {
                Content = text,
                Margin = new Thickness(8, 0, 0, 0),
                Padding = new Thickness(14, 8, 14, 8),
                Background = BrushFrom("#111D2A"),
                Foreground = textPrimary,
                BorderBrush = accent,
                BorderThickness = new Thickness(1),
                Cursor = System.Windows.Input.Cursors.Hand
            };
            button.Click += handler;
            return button;
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

        private TextBlock SpacedText(string value, double size, Brush brush)
        {
            var block = Text(value, size, FontWeights.Normal, brush);
            block.Margin = new Thickness(0, 8, 0, 0);
            block.LineHeight = size + 5;
            return block;
        }

        private void UpdateNavigationState()
        {
            foreach (var pair in navigationButtons)
            {
                var selected = pair.Key == activePage;
                var ready = IsPageContextReady(pair.Key);
                pair.Value.Background = selected ? BrushFrom("#132A45") : Brushes.Transparent;
                pair.Value.BorderBrush = selected ? BrushFrom("#2A72BD") : Brushes.Transparent;
                pair.Value.Opacity = selected || ready ? 1.0 : 0.58;
            }
        }

        private bool IsPageContextReady(string page)
        {
            if (page == "Mods")
            {
                return HasReached(WorkflowState.ModsFolderSelected);
            }
            if (page == "Plan")
            {
                return HasReached(WorkflowState.Scanned);
            }
            if (page == "Apply & Restore")
            {
                return HasReached(WorkflowState.PlanReady);
            }
            return true;
        }

        private void AdvanceState(WorkflowState state, string message)
        {
            if (state > workflowState)
            {
                workflowState = state;
            }
            SetStatus(message);
            UpdateWorkflowUi();
        }

        private bool IsCurrentWizardStep(WorkflowState completeState, WorkflowState unlockState)
        {
            return !HasReached(completeState) && HasReached(unlockState);
        }

        private bool CanApplyToStaging()
        {
            return planReviewManuallyChecked && HasReached(WorkflowState.PlanReviewed) && !HasReached(WorkflowState.Staged);
        }

        private string StagingActionLabel()
        {
            if (HasReached(WorkflowState.Staged))
            {
                return "Staging complete";
            }
            return CanApplyToStaging() ? "Apply to staging" : "Apply to staging locked";
        }

        private string GameWriteLabel()
        {
            if (HasReached(WorkflowState.RestoreAvailable))
            {
                return "Manifest available";
            }
            if (HasReached(WorkflowState.Staged))
            {
                return "Confirmation required";
            }
            return "Locked";
        }

        private void HandleTopApplyAction()
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

        private bool HasReached(WorkflowState state)
        {
            return workflowState >= state;
        }

        private string WorkflowLabel()
        {
            switch (workflowState)
            {
                case WorkflowState.NoProject: return "No project";
                case WorkflowState.ProjectOpened: return "Project opened";
                case WorkflowState.ModFamilyChosen: return "Mod family chosen";
                case WorkflowState.GameFolderSelected: return "Game folder selected";
                case WorkflowState.ModsFolderSelected: return "Mods folder selected";
                case WorkflowState.Scanned: return "Scan complete";
                case WorkflowState.PlanReady: return "Plan ready";
                case WorkflowState.PlanReviewed: return "Plan reviewed";
                case WorkflowState.Staged: return "Staged";
                case WorkflowState.GameApplied: return "Game applied";
                case WorkflowState.RestoreAvailable: return "Restore manifest available";
                default: return workflowState.ToString();
            }
        }

        private string GetNextAction()
        {
            switch (workflowState)
            {
                case WorkflowState.NoProject: return "Open a project or start Guided Setup.";
                case WorkflowState.ProjectOpened: return "Choose a mod family.";
                case WorkflowState.ModFamilyChosen: return "Choose the game folder.";
                case WorkflowState.GameFolderSelected: return "Choose the mods folder.";
                case WorkflowState.ModsFolderSelected: return "Scan mods.";
                case WorkflowState.Scanned: return "Create and review the plan.";
                case WorkflowState.PlanReady: return "Review conflicts and warnings.";
                case WorkflowState.PlanReviewed: return "Apply to staging.";
                case WorkflowState.Staged: return "Open Apply & Restore and confirm game apply.";
                case WorkflowState.GameApplied: return "Inspect the game apply manifest.";
                case WorkflowState.RestoreAvailable: return "Preview restore or inspect the latest manifest.";
                default: return "Preview restore or inspect the manifest.";
            }
        }

        private void UpdateWorkflowUi()
        {
            if (workflowChipText != null)
            {
                workflowChipText.Text = "State: " + WorkflowLabel();
            }
            if (safetyChipText != null)
            {
                safetyChipText.Text = "Safe mode: Dry-run first | No startup scan | Python " + (sidecar.HasProbed ? "checked" : "idle");
            }

            SetButtonState(scanButton, HasReached(WorkflowState.ModsFolderSelected));
            SetButtonState(planButton, HasReached(WorkflowState.Scanned));
            SetButtonState(applyButton, HasReached(WorkflowState.Staged));

            if (applyButton != null)
            {
                if (HasReached(WorkflowState.RestoreAvailable))
                {
                    applyButton.Content = "Preview restore";
                    applyButton.BorderBrush = accentBlue;
                }
                else if (HasReached(WorkflowState.Staged))
                {
                    applyButton.Content = "Open game confirm";
                    applyButton.BorderBrush = accentRed;
                }
                else
                {
                    applyButton.Content = "Apply to game locked";
                    applyButton.BorderBrush = panelBorder;
                }
            }
            RenderStatusBar();
        }

        private void SetButtonState(Button button, bool enabled)
        {
            if (button == null)
            {
                return;
            }
            button.IsEnabled = enabled;
            button.Opacity = enabled ? 1.0 : 0.45;
        }

        private void SetStatus(string message)
        {
            statusMessage = message;
            RenderStatusBar();
        }

        private void RenderStatusBar()
        {
            if (statusText != null)
            {
                statusText.Text = WorkflowLabel() + " - " + (string.IsNullOrEmpty(statusMessage) ? GetNextAction() : statusMessage);
            }
        }

        private static Brush BrushFrom(string value)
        {
            return (Brush)new BrushConverter().ConvertFromString(value);
        }
    }
}
