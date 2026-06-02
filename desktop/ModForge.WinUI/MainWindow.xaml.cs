using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Text.Json;
using System.Threading.Tasks;
using Microsoft.UI;
using Microsoft.UI.Dispatching;
using Microsoft.UI.Windowing;
using Microsoft.UI.Xaml;
using Microsoft.UI.Xaml.Controls;
using Microsoft.UI.Xaml.Media;
using Windows.Graphics;
using Windows.Storage.Pickers;
using Windows.UI;
using Windows.UI.Text;

namespace ModForge.WinUI;

public sealed partial class MainWindow : Window
{
    private readonly List<ModRow> mods;
    private readonly List<ConflictRow> conflicts;
    private readonly List<string> warnings;
    private readonly List<ProfileOption> profileOptions;
    private readonly PythonCoreService pythonCore = new();
    private AppWindow? appWindow;
    private DispatcherQueueTimer? windowSizeSaveTimer;
    private SizeInt32 pendingWindowSize;
    private CoreProject? currentProject;
    private CorePlan? currentPlan;
    private CoreManifest? stagingManifest;
    private string selectedProfileId = "mhw-reframework";
    private string selectedGameFolder = "";
    private string selectedModsFolder = "";
    private WorkflowState workflowState = WorkflowState.NoProject;
    private string activePage = "Home";
    private string selectedFamily = "Not selected";
    private string statusMessage = "Start Guided Setup to open a project safely.";
    private bool isBusy;
    private bool profilesLoaded;
    private bool profilesLoading;
    private bool planReviewManuallyChecked;

    public MainWindow()
    {
        InitializeComponent();
        Title = "ModForge Manager";
        mods = new List<ModRow>();
        conflicts = new List<ConflictRow>();
        warnings = new List<string>();
        profileOptions = new List<ProfileOption>();
        SeedFallbackProfiles();
        ConfigureWindowPersistence();
        ShellNav.SelectedItem = NavHome;
        ShowPage("Home");
    }

    private async void OpenProjectButton_Click(object sender, RoutedEventArgs e)
    {
        await OpenProjectAsync();
    }

    private async void ScanButton_Click(object sender, RoutedEventArgs e)
    {
        await ScanProjectAsync();
    }

    private async void PlanButton_Click(object sender, RoutedEventArgs e)
    {
        await CreatePlanAsync();
    }

    private void ApplyButton_Click(object sender, RoutedEventArgs e)
    {
        ShowPage("Apply & Restore");
        if (HasReached(WorkflowState.RestoreAvailable))
        {
            SetStatus("Game manifest is available. View the latest manifest or staged records.");
        }
        else if (HasReached(WorkflowState.Staged))
        {
            SetStatus("Staging is complete. View the staging manifest or open the staging folder.");
        }
        else
        {
            SetStatus("Apply to game is locked until staging is complete.");
        }
    }

    private async Task OpenGuidedSetupAsync()
    {
        ShowPage("Guided Setup");
        await EnsureProfilesLoadedAsync();
    }

    private async Task EnsureProfilesLoadedAsync(bool force = false)
    {
        if (profilesLoading || isBusy)
        {
            return;
        }
        if (profilesLoaded && !force)
        {
            return;
        }

        await RunCoreActionAsync("Loading game profile catalog through Python...", async () =>
        {
            profilesLoading = true;
            try
            {
                var loaded = await pythonCore.ListProfilesAsync();
                profileOptions.Clear();
                profileOptions.AddRange(loaded.Select(ProfileOption.FromCore));
                if (profileOptions.Count == 0)
                {
                    SeedFallbackProfiles();
                }

                profilesLoaded = true;
                SetStatus($"Profile catalog loaded: {profileOptions.Count} profiles available.");
            }
            finally
            {
                profilesLoading = false;
            }
        });
    }

    private async Task OpenProjectAsync()
    {
        var projectFile = await PickProjectFileAsync();
        if (string.IsNullOrWhiteSpace(projectFile))
        {
            SetStatus("Open project canceled.");
            return;
        }

        await LoadProjectAsync(projectFile);
    }

    private async Task LoadProjectAsync(string projectFile)
    {
        await RunCoreActionAsync("Loading project through Python...", async () =>
        {
            currentProject = await pythonCore.LoadProjectAsync(projectFile);
            selectedFamily = currentProject.ProfileName;
            selectedProfileId = currentProject.ProfileId;
            selectedGameFolder = currentProject.GameRoot;
            selectedModsFolder = currentProject.ModsDir;
            ResetCoreResults();
            workflowState = WorkflowState.ModsFolderSelected;
            SetStatus("Project loaded. Scan Mods is now available.");
            ShowPage("Guided Setup");
        });
    }

    private async Task ChooseGameFolderAsync()
    {
        var folder = await PickFolderAsync();
        if (string.IsNullOrWhiteSpace(folder))
        {
            SetStatus("Game folder selection canceled.");
            return;
        }

        await CreateOrLoadManagedProjectAsync(folder);
    }

    private async Task CreateOrLoadManagedProjectAsync(string gameFolder)
    {
        var paths = ManagedProjectPathsFor(gameFolder);
        Directory.CreateDirectory(paths.ProjectDirectory);
        Directory.CreateDirectory(paths.ModsDirectory);

        if (File.Exists(paths.ProjectFile))
        {
            await LoadProjectAsync(paths.ProjectFile);
            SetStatus("Existing managed project loaded. Scan Mods is now available.");
            return;
        }

        selectedGameFolder = gameFolder;
        selectedModsFolder = paths.ModsDirectory;
        currentProject = null;
        ResetCoreResults();

        await RunCoreActionAsync("Creating managed project and Mods folder...", async () =>
        {
            currentProject = await pythonCore.CreateProjectAsync(
                SuggestedProjectName(gameFolder),
                gameFolder,
                paths.ModsDirectory,
                paths.StagingDirectory,
                selectedProfileId,
                paths.ProjectFile);
            selectedFamily = currentProject.ProfileName;
            selectedProfileId = currentProject.ProfileId;
            selectedGameFolder = currentProject.GameRoot;
            selectedModsFolder = currentProject.ModsDir;
            workflowState = WorkflowState.ModsFolderSelected;
            SetStatus("Managed project created with a default Mods folder. Scan Mods is now available.");
            ShowPage("Guided Setup");
        });
    }

    private async Task ChangeModsFolderAsync()
    {
        var folder = await PickFolderAsync();
        if (string.IsNullOrWhiteSpace(folder))
        {
            SetStatus("Mods folder change canceled.");
            return;
        }

        if (currentProject == null)
        {
            if (string.IsNullOrWhiteSpace(selectedGameFolder))
            {
                SetStatus("Choose a game folder before changing the managed Mods folder.");
                return;
            }

            var paths = ManagedProjectPathsFor(selectedGameFolder);
            Directory.CreateDirectory(paths.ProjectDirectory);
            await RunCoreActionAsync("Creating project with the selected Mods folder...", async () =>
            {
                currentProject = await pythonCore.CreateProjectAsync(
                    SuggestedProjectName(selectedGameFolder),
                    selectedGameFolder,
                    folder,
                    paths.StagingDirectory,
                    selectedProfileId,
                    paths.ProjectFile);
                selectedFamily = currentProject.ProfileName;
                selectedProfileId = currentProject.ProfileId;
                selectedGameFolder = currentProject.GameRoot;
                selectedModsFolder = currentProject.ModsDir;
                workflowState = WorkflowState.ModsFolderSelected;
                SetStatus("Project created with the selected Mods folder. Scan Mods is now available.");
                ShowPage("Guided Setup");
            });
            return;
        }

        selectedModsFolder = folder;
        var projectFile = currentProject.ProjectFile;
        await RunCoreActionAsync("Changing project Mods folder...", async () =>
        {
            currentProject = await pythonCore.UpdateProjectPathsAsync(
                projectFile,
                modsDir: folder);
            selectedFamily = currentProject.ProfileName;
            selectedProfileId = currentProject.ProfileId;
            selectedGameFolder = currentProject.GameRoot;
            selectedModsFolder = currentProject.ModsDir;
            ResetCoreResults();
            workflowState = WorkflowState.ModsFolderSelected;
            SetStatus("Mods folder changed. Scan Mods is now available.");
            ShowPage("Guided Setup");
        });
    }

    private async Task ScanProjectAsync()
    {
        if (currentProject == null)
        {
            SetStatus("Open or create a project before scanning.");
            ShowPage("Guided Setup");
            return;
        }

        await RunCoreActionAsync("Scanning mods through Python...", async () =>
        {
            await RefreshScanOnlyAsync();
            conflicts.Clear();
            warnings.Clear();
            currentPlan = null;
            stagingManifest = null;
            planReviewManuallyChecked = false;
            workflowState = WorkflowState.Scanned;
            SetStatus($"Scan complete: {mods.Count} mods found. No files were changed.");
            ShowPage("Mods");
        });
    }

    private async Task SetModEnabledAsync(ModRow mod, bool enabled)
    {
        if (currentProject == null)
        {
            SetStatus("Open or create a project before changing mod state.");
            return;
        }

        var verb = enabled ? "Enabling" : "Disabling";
        await RunCoreActionAsync($"{verb} {mod.Name} through Python...", async () =>
        {
            await pythonCore.SetModEnabledAsync(currentProject.ProjectFile, mod.Id, enabled);
            if (currentPlan != null || HasReached(WorkflowState.PlanReady))
            {
                await RefreshScanAndPlanAsync();
                workflowState = WorkflowState.PlanReady;
                planReviewManuallyChecked = false;
                stagingManifest = null;
                SetStatus($"{mod.Name} {(enabled ? "enabled" : "disabled")}. Dry-run plan rebuilt; review is required before staging.");
            }
            else
            {
                await RefreshScanOnlyAsync();
                conflicts.Clear();
                warnings.Clear();
                currentPlan = null;
                stagingManifest = null;
                planReviewManuallyChecked = false;
                workflowState = WorkflowState.Scanned;
                SetStatus($"{mod.Name} {(enabled ? "enabled" : "disabled")}. Scan refreshed; create a plan before staging.");
            }

            ShowPage("Mods");
        });
    }

    private async Task CreatePlanAsync()
    {
        if (currentProject == null)
        {
            SetStatus("Open or create a project before planning.");
            ShowPage("Guided Setup");
            return;
        }

        await RunCoreActionAsync("Creating dry-run plan through Python...", async () =>
        {
            currentPlan = await pythonCore.CreatePlanAsync(currentProject.ProjectFile);
            conflicts.Clear();
            foreach (var conflict in currentPlan.Conflicts)
            {
                conflicts.Add(new ConflictRow(conflict.Destination, conflict.WinningMod, conflict.LosingMod, conflict.Risk, conflict.Participants, conflict.Sources));
            }

            warnings.Clear();
            warnings.AddRange(currentPlan.Warnings);
            ApplyConflictCountsToMods();
            stagingManifest = null;
            planReviewManuallyChecked = false;
            workflowState = WorkflowState.PlanReady;
            SetStatus($"Dry-run plan ready: {currentPlan.Operations} operations, {currentPlan.Conflicts.Count} conflicts, {currentPlan.Warnings.Count} warnings.");
            ShowPage("Plan");
        });
    }

    private async Task PreferConflictWinnerAsync(ConflictRow conflict, string preferredModName)
    {
        if (currentProject == null)
        {
            SetStatus("Open or create a project before changing priority.");
            return;
        }

        var preferred = mods.FirstOrDefault(item => string.Equals(item.Name, preferredModName, StringComparison.OrdinalIgnoreCase));
        if (preferred == null || string.IsNullOrWhiteSpace(preferred.Id))
        {
            SetStatus("Could not find scanned mod id for " + preferredModName + ".");
            return;
        }

        var ordered = mods
            .OrderBy(item => item.Priority)
            .Select(item => item.Id)
            .Where(item => !string.IsNullOrWhiteSpace(item))
            .Distinct(StringComparer.OrdinalIgnoreCase)
            .ToList();
        ordered.RemoveAll(item => string.Equals(item, preferred.Id, StringComparison.OrdinalIgnoreCase));
        ordered.Add(preferred.Id);

        await RunCoreActionAsync("Updating priority and rebuilding the dry-run plan...", async () =>
        {
            await pythonCore.SetPriorityAsync(currentProject.ProjectFile, ordered);
            await RefreshScanAndPlanAsync();
            workflowState = WorkflowState.PlanReady;
            planReviewManuallyChecked = false;
            stagingManifest = null;
            SetStatus($"{preferred.Name} now has the highest priority. Review the updated plan before staging.");
            ShowPage("Plan");
        });
    }

    private async Task RefreshScanAndPlanAsync()
    {
        if (currentProject == null)
        {
            throw new PythonCoreException("Open or create a project before refreshing the plan.");
        }

        await RefreshScanOnlyAsync();

        currentPlan = await pythonCore.CreatePlanAsync(currentProject.ProjectFile);
        conflicts.Clear();
        foreach (var item in currentPlan.Conflicts)
        {
            conflicts.Add(new ConflictRow(item.Destination, item.WinningMod, item.LosingMod, item.Risk, item.Participants, item.Sources));
        }

        warnings.Clear();
        warnings.AddRange(currentPlan.Warnings);
        ApplyConflictCountsToMods();
    }

    private async Task RefreshScanOnlyAsync()
    {
        if (currentProject == null)
        {
            throw new PythonCoreException("Open or create a project before scanning.");
        }

        mods.Clear();
        foreach (var mod in await pythonCore.ScanModsAsync(currentProject.ProjectFile))
        {
            mods.Add(ToModRow(mod));
        }
    }

    private async Task ApplyStagingAsync()
    {
        if (currentProject == null)
        {
            SetStatus("Open or create a project before staging.");
            return;
        }

        if (!CanApplyToStaging())
        {
            SetStatus("Review the plan manually before applying to staging.");
            return;
        }

        await RunCoreActionAsync("Applying to staging through Python...", async () =>
        {
            stagingManifest = await pythonCore.ApplyStagingAsync(currentProject.ProjectFile);
            workflowState = WorkflowState.Staged;
            SetStatus($"Applied to staging: {stagingManifest.Copied} copied, {stagingManifest.Overwritten} overwritten, {stagingManifest.Skipped} skipped.");
            ShowPage("Apply & Restore");
        });
    }

    private async Task ShowStagingManifestAsync()
    {
        var manifest = await EnsureStagingManifestAsync();
        if (manifest == null)
        {
            return;
        }

        var details = string.Join(Environment.NewLine, new[]
        {
            $"Manifest id: {manifest.ManifestId}",
            $"Target: {manifest.Target}",
            $"Applied: {manifest.AppliedAt}",
            $"Copied: {manifest.Copied}",
            $"Overwritten: {manifest.Overwritten}",
            $"Skipped: {manifest.Skipped}",
            $"Target root: {manifest.TargetRoot}",
            $"Manifest path: {manifest.ManifestPath}"
        });
        var body = new TextBlock
        {
            Text = details,
            FontFamily = new FontFamily("Cascadia Mono"),
            FontSize = 13,
            Foreground = White,
            TextWrapping = TextWrapping.Wrap
        };
        var dialog = new ContentDialog
        {
            XamlRoot = ContentHost.XamlRoot,
            Title = "Staging manifest",
            Content = new ScrollViewer
            {
                MaxHeight = 420,
                Content = body
            },
            CloseButtonText = "Close",
            DefaultButton = ContentDialogButton.Close
        };
        await dialog.ShowAsync();
        SetStatus("Staging manifest displayed: " + manifest.ManifestId);
    }

    private async Task OpenStagingFolderAsync()
    {
        var manifest = await EnsureStagingManifestAsync();
        if (manifest == null || currentProject == null)
        {
            return;
        }

        if (!Directory.Exists(currentProject.StagingDir))
        {
            SetStatus("Staging folder is missing. Apply to staging again.");
            return;
        }

        try
        {
            Process.Start(new ProcessStartInfo
            {
                FileName = currentProject.StagingDir,
                UseShellExecute = true
            });
            SetStatus("Opened staging folder: " + currentProject.StagingDir);
        }
        catch (Exception ex)
        {
            SetStatus("Could not open staging folder: " + ex.Message);
        }
    }

    private async Task<CoreManifest?> EnsureStagingManifestAsync()
    {
        if (currentProject == null)
        {
            SetStatus("Open or create a project before viewing staging results.");
            return null;
        }

        if (!HasReached(WorkflowState.Staged))
        {
            SetStatus("Apply to staging before viewing the staging manifest.");
            return null;
        }

        if (stagingManifest != null)
        {
            return stagingManifest;
        }

        try
        {
            stagingManifest = await pythonCore.LoadStagingManifestAsync(currentProject.ProjectFile);
            return stagingManifest;
        }
        catch (PythonCoreException ex)
        {
            SetStatus(ex.Message);
            return null;
        }
    }

    private async Task PreviewStagingRecordsAsync()
    {
        if (currentProject == null)
        {
            SetStatus("Open or create a project before viewing staged records.");
            return;
        }

        if (!CanPreviewStagingRecords())
        {
            SetStatus("Apply to staging first. Staged records stay read-only and game apply remains locked.");
            return;
        }

        await RunCoreActionAsync("Loading staged records...", async () =>
        {
            var manifest = await EnsureStagingManifestAsync();
            if (manifest == null)
            {
                return;
            }

            await ShowStagingRecordsDialogAsync(manifest);
            SetStatus($"Staged records ready: {manifest.Records.Count} records in the staging manifest.");
        });
    }

    private async Task ShowStagingRecordsDialogAsync(CoreManifest manifest)
    {
        var lines = new List<string>
        {
            $"Manifest id: {manifest.ManifestId}",
            $"Manifest path: {manifest.ManifestPath}",
            $"Target root: {manifest.TargetRoot}",
            $"Copied: {manifest.Copied}",
            $"Overwritten: {manifest.Overwritten}",
            $"Skipped: {manifest.Skipped}",
            $"Records: {manifest.Records.Count}"
        };
        foreach (var record in manifest.Records.Take(100))
        {
            var backup = string.IsNullOrWhiteSpace(record.BackupPath) ? "" : " | backup prepared";
            lines.Add($"- {record.DestinationPath}: {record.Status} (mod={record.SourceMod}){backup}");
        }
        if (manifest.Records.Count > 100)
        {
            lines.Add($"... {manifest.Records.Count - 100} more records omitted from this preview.");
        }

        var body = new TextBlock
        {
            Text = string.Join(Environment.NewLine, lines),
            FontFamily = new FontFamily("Cascadia Mono"),
            FontSize = 13,
            Foreground = White,
            TextWrapping = TextWrapping.Wrap
        };
        var dialog = new ContentDialog
        {
            XamlRoot = ContentHost.XamlRoot,
            Title = "Staging output preview",
            Content = new ScrollViewer
            {
                MaxHeight = 500,
                Content = body
            },
            CloseButtonText = "Close",
            DefaultButton = ContentDialogButton.Close
        };
        await dialog.ShowAsync();
    }

    private async Task RunCoreActionAsync(string busyMessage, Func<Task> action)
    {
        if (isBusy)
        {
            SetStatus("A Python action is already running.");
            return;
        }

        try
        {
            isBusy = true;
            SetStatus(busyMessage);
            await action();
        }
        catch (PythonCoreException ex)
        {
            SetStatus(ex.Message);
        }
        catch (Exception ex)
        {
            SetStatus("Action failed: " + ex.Message);
        }
        finally
        {
            isBusy = false;
            ShowPage(activePage);
        }
    }

    private async Task<string?> PickProjectFileAsync()
    {
        var picker = new FileOpenPicker();
        picker.FileTypeFilter.Add(".json");
        picker.FileTypeFilter.Add(".mfproj");
        picker.SuggestedStartLocation = PickerLocationId.DocumentsLibrary;
        InitializePicker(picker);
        var file = await picker.PickSingleFileAsync();
        return file?.Path;
    }

    private async Task<string?> PickFolderAsync()
    {
        var picker = new FolderPicker
        {
            SuggestedStartLocation = PickerLocationId.ComputerFolder
        };
        picker.FileTypeFilter.Add("*");
        InitializePicker(picker);
        var folder = await picker.PickSingleFolderAsync();
        return folder?.Path;
    }

    private void InitializePicker(object picker)
    {
        var hwnd = WinRT.Interop.WindowNative.GetWindowHandle(this);
        WinRT.Interop.InitializeWithWindow.Initialize(picker, hwnd);
    }

    private async void ShellNav_SelectionChanged(NavigationView sender, NavigationViewSelectionChangedEventArgs args)
    {
        if (args.SelectedItemContainer?.Tag is string page)
        {
            if (page == "Guided Setup")
            {
                await OpenGuidedSetupAsync();
            }
            else
            {
                ShowPage(page);
            }
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
                PrimaryButton(HasReached(WorkflowState.ProjectOpened) ? "Continue Guided Setup" : "Start Guided Setup", AccentBlue, async (_, _) => await OpenGuidedSetupAsync()),
                PrimaryButton("Open Project", AccentGreen, async (_, _) => await OpenProjectAsync())),
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
        steps.Children.Add(CompactWizardStep(1, "Choose game profile", ProfileStepDetail(), ProfilePicker(), WorkflowState.ModFamilyChosen, WorkflowState.NoProject));
        steps.Children.Add(CompactWizardStep(2, "Select game folder", selectedGameFolder.Length > 0 ? selectedGameFolder + " · managed project is automatic" : "Choose the game root. ModForge will create the project and default Mods folder.", WizardButton(selectedGameFolder.Length > 0 ? "Change game folder" : "Choose game folder", IsCurrentStep(WorkflowState.GameFolderSelected, WorkflowState.ModFamilyChosen) || HasReached(WorkflowState.GameFolderSelected), async (_, _) => await ChooseGameFolderAsync()), WorkflowState.GameFolderSelected, WorkflowState.ModFamilyChosen));
        steps.Children.Add(CompactWizardStep(3, "Mods folder", selectedModsFolder.Length > 0 ? selectedModsFolder : "Default: Documents\\ModForge Manager\\Projects\\<game>\\Mods", WizardButton("Change mods folder", HasReached(WorkflowState.GameFolderSelected) && !isBusy, async (_, _) => await ChangeModsFolderAsync()), WorkflowState.ModsFolderSelected, WorkflowState.GameFolderSelected));
        steps.Children.Add(CompactWizardStep(4, "Scan mods", "Read-only Python scan. No files will be changed.", WizardButton(HasReached(WorkflowState.Scanned) ? "Scan again" : "Scan now", CanScan(), async (_, _) => await ScanProjectAsync()), WorkflowState.Scanned, WorkflowState.ModsFolderSelected));
        steps.Children.Add(CompactWizardStep(5, "Review plan and conflicts", "Create a dry-run plan, then inspect winners, overwritten destinations, and warnings.", WizardButton(HasReached(WorkflowState.PlanReady) ? "Rebuild plan" : "Create plan", CanCreatePlan(), async (_, _) => await CreatePlanAsync()), WorkflowState.PlanReviewed, WorkflowState.Scanned));
        steps.Children.Add(CompactWizardStep(6, "Apply to staging", "First write step. The game folder is still untouched.", WizardButton(StagingActionLabel(), CanApplyToStaging(), async (_, _) => await ApplyStagingAsync()), WorkflowState.Staged, WorkflowState.PlanReviewed));
        steps.Children.Add(CompactWizardStep(7, "Apply to game", "Locked for safety in the public preview. Inspect staging first.", WizardButton(HasReached(WorkflowState.Staged) ? "Open staging result" : "Game apply locked", HasReached(WorkflowState.Staged), (_, _) => { ShowPage("Apply & Restore"); SetStatus("Game apply is locked for safety in this public preview. Review the staging manifest first."); }), WorkflowState.RestoreAvailable, WorkflowState.Staged));

        return Panel(steps);
    }

    private UIElement BuildMods()
    {
        if (!HasReached(WorkflowState.Scanned))
        {
            return EmptyActionPage(
                "No scan results yet.",
                "Select a game profile, game folder, and mods folder before scanning. Scan is read-only and does not change files.",
                "Scan Mods",
                CanScan(),
                async (_, _) => await ScanProjectAsync(),
                new[] { StepStateText("Project", WorkflowState.ProjectOpened), StepStateText("Profile", WorkflowState.ModFamilyChosen), StepStateText("Game folder", WorkflowState.GameFolderSelected), StepStateText("Mods folder", WorkflowState.ModsFolderSelected) });
        }

        if (mods.Count == 0)
        {
            return EmptyActionPage(
                "No mods found.",
                "The selected mods folder was scanned, but no mod packages were detected. Choose another project or scan again after adding mods.",
                "Scan again",
                CanScan(),
                async (_, _) => await ScanProjectAsync(),
                new[] { CurrentProjectLine(), "Python scan completed without changing files." });
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
                async (_, _) => await CreatePlanAsync(),
                new[] { StepStateText("Scan", WorkflowState.Scanned), "Plan review: pending", "Staging: locked" });
        }

        var grid = TwoColumnGrid(1.45, 1.0);
        var left = Stack();
        Grid.SetColumn(left, 0);
        grid.Children.Add(left);
        left.Children.Add(Panel(Stack(
            Text("Plan Summary", 22, SemiBoldWeight, White),
            Line("Copy to staging", $"{currentPlan?.WinningOperations ?? 0} winning operations", AccentGreen),
            Line("Destination conflicts", $"{conflicts.Count} conflicts", conflicts.Count > 0 ? AccentRed : AccentGreen),
            Line("Warnings", $"{warnings.Count} review items", warnings.Count > 0 ? AccentAmber : AccentGreen))));

        left.Children.Add(SectionTitle("Conflict details"));
        if (conflicts.Count == 0)
        {
            left.Children.Add(InfoPanel("No destination conflicts", new[]
            {
                "No two enabled mods write to the same destination in the latest dry-run plan."
            }));
        }
        else
        {
            var conflictList = new ListView
            {
                Background = Brush("#0F1721"),
                BorderBrush = Brush("#243141"),
                BorderThickness = new Thickness(1),
                CornerRadius = new CornerRadius(8)
            };
            foreach (var conflict in conflicts)
            {
                conflictList.Items.Add(ConflictListRow(conflict));
            }
            left.Children.Add(conflictList);
        }

        var right = Stack();
        Grid.SetColumn(right, 1);
        grid.Children.Add(right);
        right.Children.Add(InfoPanel("Warnings", warnings));
        right.Children.Add(InfoPanel("Conflict priority", new[]
        {
            "The winner is the enabled mod with the highest priority for the same destination.",
            "Use the Prefer buttons in a conflict row to move a mod to the end of the active priority order.",
            "Changing priority rebuilds the dry-run plan and locks staging until you review it again."
        }));

        var checkbox = new CheckBox
        {
            Content = "I reviewed the conflict and warning lists",
            Foreground = White,
            IsChecked = planReviewManuallyChecked,
            IsEnabled = !planReviewManuallyChecked && !HasReached(WorkflowState.Staged),
            Margin = new Thickness(0, 14, 0, 12)
        };
        var staging = PrimaryButton(StagingActionLabel(), AccentGreen, async (_, _) => await ApplyStagingAsync());
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
                "Create and review a plan before staging, game apply, manifests, or recovery actions become available.",
                "Open Plan",
                CanCreatePlan(),
                async (_, _) => await CreatePlanAsync(),
                new[] { StepStateText("Scan", WorkflowState.Scanned), "Plan: required", "Staging: locked", "Restore: locked" });
        }

        var grid = TwoColumnGrid(1.1, 1.0);
        var left = Stack();
        Grid.SetColumn(left, 0);
        grid.Children.Add(left);

        var staging = PrimaryButton(StagingActionLabel(), AccentGreen, async (_, _) => await ApplyStagingAsync());
        staging.IsEnabled = CanApplyToStaging();
        var viewStaging = PrimaryButton("View staging manifest", AccentBlue, async (_, _) => await ShowStagingManifestAsync());
        viewStaging.IsEnabled = HasReached(WorkflowState.Staged) && !isBusy;
        var openStaging = PrimaryButton("Open staging folder", AccentBlue, async (_, _) => await OpenStagingFolderAsync());
        openStaging.IsEnabled = HasReached(WorkflowState.Staged) && !isBusy;
        left.Children.Add(Panel(Stack(
            Text("Staging actions", 22, SemiBoldWeight, White),
            Spaced("Staging writes to the configured staging folder first. It does not touch the game folder.", 13, Secondary),
            ButtonRow(staging, viewStaging, openStaging))));

        left.Children.Add(GameApplyPanel());

        var right = Stack();
        Grid.SetColumn(right, 1);
        grid.Children.Add(right);
        right.Children.Add(ManifestPanel());

        var preview = PrimaryButton("Preview staged records", AccentBlue, async (_, _) => await PreviewStagingRecordsAsync());
        var gameWrites = PrimaryButton("Game writes locked", AccentAmber, (_, _) => SetStatus("Game-folder writes remain locked in this public preview."));
        var destructive = PrimaryButton("Destructive actions locked", AccentRed, (_, _) => SetStatus("Destructive recovery actions are not wired in this public preview."));
        preview.IsEnabled = CanPreviewStagingRecords();
        gameWrites.IsEnabled = false;
        destructive.IsEnabled = false;
        right.Children.Add(Panel(Stack(
            Text("Staged output", 20, SemiBoldWeight, White),
            Spaced("Inspect the manifest records created by staging. Game-folder writes and destructive recovery stay locked.", 13, Secondary),
            ButtonRow(preview, gameWrites, destructive))));
        return grid;
    }

    private UIElement GameApplyPanel()
    {
        var stack = Stack();
        var title = HasReached(WorkflowState.RestoreAvailable) ? "Game manifest available" : "Game apply confirm zone";
        stack.Children.Add(Text(title, 22, SemiBoldWeight, HasReached(WorkflowState.Staged) ? AccentRed : White));

        if (!HasReached(WorkflowState.Staged))
        {
            var locked = PrimaryButton("Game apply locked", Brush("#243141"), (_, _) => SetStatus("Apply to staging first. Game apply is locked for safety in this public preview."));
            locked.IsEnabled = false;
            stack.Children.Add(Spaced("Game apply stays locked until the staging flow is proven.", 13, Secondary));
            stack.Children.Add(ButtonRow(locked));
        }
        else if (HasReached(WorkflowState.RestoreAvailable))
        {
            stack.Children.Add(Spaced("Game apply is complete. The primary actions are now manifest inspection and staged record review.", 13, Secondary));
            stack.Children.Add(ButtonRow(
                PrimaryButton("View latest manifest", AccentBlue, (_, _) => SetStatus("Latest manifest is ready for inspection.")),
                PrimaryButton("Preview staged records", AccentGreen, async (_, _) => await PreviewStagingRecordsAsync())));
        }
        else
        {
            var confirm = PrimaryButton("Game apply locked", Brush("#2A1620"), (_, _) => SetStatus("Game apply is locked for safety in this public preview."));
            confirm.IsEnabled = false;
            stack.Children.Add(Spaced("Staging is complete, but writing to the game folder remains locked in this public preview. Review the staging manifest first.", 13, Secondary));
            stack.Children.Add(ButtonRow(confirm, PrimaryButton("View staging manifest", AccentBlue, async (_, _) => await ShowStagingManifestAsync())));
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

    private UIElement ProfilePicker()
    {
        if (profileOptions.Count == 0)
        {
            return ButtonRow(WizardButton("Load profiles", !isBusy, async (_, _) => await EnsureProfilesLoadedAsync(force: true)));
        }

        var chosen = SelectedProfileOption() ?? profileOptions[0];
        var combo = new ComboBox
        {
            MinWidth = 280,
            MaxWidth = 320,
            PlaceholderText = "Select game profile",
            IsEnabled = !isBusy,
            Background = Brush("#111D2A"),
            Foreground = White
        };

        foreach (var option in profileOptions)
        {
            var item = new ComboBoxItem
            {
                Content = ProfilePickerLabel(option),
                Tag = option
            };
            combo.Items.Add(item);
            if (string.Equals(option.Id, selectedProfileId, StringComparison.OrdinalIgnoreCase))
            {
                combo.SelectedItem = item;
                chosen = option;
            }
        }

        combo.SelectionChanged += (_, _) =>
        {
            if (combo.SelectedItem is ComboBoxItem { Tag: ProfileOption option })
            {
                chosen = option;
            }
        };

        var detail = Spaced(ProfileDetail(chosen), 12, Secondary);
        var use = WizardButton(HasReached(WorkflowState.ModFamilyChosen) ? "Use profile" : "Use selected", !isBusy, (_, _) => SelectProfile(chosen));
        var refresh = WizardButton(profilesLoaded ? "Refresh" : "Load catalog", !isBusy, async (_, _) => await EnsureProfilesLoadedAsync(force: true));

        return Stack(combo, detail, ButtonRow(use, refresh));
    }

    private void SelectProfile(ProfileOption option)
    {
        selectedFamily = option.DisplayName;
        selectedProfileId = option.Id;
        currentProject = null;
        ResetCoreResults();
        selectedGameFolder = "";
        selectedModsFolder = "";
        workflowState = WorkflowState.NoProject;
        AdvanceState(WorkflowState.ModFamilyChosen, option.DisplayName + " profile selected. Choose the game folder next.");
        ShowPage("Guided Setup");
    }

    private ProfileOption? SelectedProfileOption()
    {
        return profileOptions.FirstOrDefault(option => string.Equals(option.Id, selectedProfileId, StringComparison.OrdinalIgnoreCase));
    }

    private string ProfileStepDetail()
    {
        if (HasReached(WorkflowState.ModFamilyChosen))
        {
            return $"{selectedFamily} ({selectedProfileId})";
        }
        return profilesLoaded
            ? "Searchable catalog loaded from Python profiles. Pick one profile before choosing folders."
            : "Profile catalog loads on this user action. No scan or file write starts here.";
    }

    private void SeedFallbackProfiles()
    {
        profileOptions.Clear();
        profileOptions.AddRange(new[]
        {
            new ProfileOption("mhw-reframework", "Monster Hunter Wilds / REFramework NativePC Workflow", "reframework", "Built-in profile for REFramework and nativePC package roots.", "builtin", 2, false),
            new ProfileOption("stellar-blade.experimental", "Stellar Blade / CNS Experimental", "unreal", "Experimental profile for Unreal archive sidecars, CNS JSON sidecars, and UE4SS runtime paths.", "builtin", 6, true),
            new ProfileOption("sts2-mods", "Slay the Spire 2 Mods Folder", "godot", "Built-in profile for standalone PCK files and loose STS2 mod folders.", "builtin", 3, false),
            new ProfileOption("unreal-pak", "Unreal PAK ~mods Workflow", "unreal", "Generic Unreal archive-as-is profile for Content/Paks/~mods.", "builtin", 7, false),
            new ProfileOption("generic-folder", "Generic Folder Game", "generic", "Direct relative-path mapping for simple folder-based games.", "builtin", 1, false)
        });
    }

    private static string ProfilePickerLabel(ProfileOption option)
    {
        var marker = option.IsExperimental ? "Experimental" : option.TrustLevel == "custom" ? "Custom" : "Built-in";
        return $"{option.DisplayName}  [{marker}]";
    }

    private static string ProfileDetail(ProfileOption option)
    {
        var family = string.IsNullOrWhiteSpace(option.Family) ? "profile" : option.Family;
        var marker = option.IsExperimental ? "Experimental" : option.TrustLevel == "custom" ? "Custom" : "Built-in";
        var description = string.IsNullOrWhiteSpace(option.Description) ? option.Id : option.Description;
        return $"{marker} · {family} · {option.RuleCount} rules · {description}";
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

        stack.Children.Add(ManifestRow(stagingManifest?.ManifestId ?? "staging-latest", "Staging", "Created by staging", StagingManifestStatus()));
        if (!HasReached(WorkflowState.RestoreAvailable))
        {
            stack.Children.Add(ManifestRow("game-apply", "Game", "Locked for preview", "Game-folder writes remain locked in the WinUI public preview."));
            return Panel(stack);
        }

        stack.Children.Add(ManifestRow("game-latest", "Game", "Available", "Tracks files written to the game folder."));
        return Panel(stack);
    }

    private UIElement ProjectSummaryPanel()
    {
        var stack = Stack(
            Text(currentProject?.Name ?? (HasReached(WorkflowState.ProjectOpened) ? "Project draft" : "No project open"), 22, SemiBoldWeight, White));
        if (HasReached(WorkflowState.ProjectOpened))
        {
            stack.Children.Add(PathLine("Project file", currentProject?.ProjectFile ?? "Managed project will be created after game folder selection"));
            stack.Children.Add(PathLine("Mods folder", selectedModsFolder.Length > 0 ? selectedModsFolder : "Managed Mods folder will be created automatically"));
            if (currentProject != null)
            {
                stack.Children.Add(ButtonRow(WizardButton("Change mods folder", !isBusy, async (_, _) => await ChangeModsFolderAsync())));
            }
        }
        else
        {
            stack.Children.Add(Spaced("Open a project or start Guided Setup. New projects get a managed Mods folder automatically.", 12, Secondary));
        }

        stack.Children.Add(Line("Profile", HasReached(WorkflowState.ModFamilyChosen) ? selectedFamily : "Not selected", AccentBlue));
        stack.Children.Add(Line("Enabled mods", HasReached(WorkflowState.Scanned) ? $"{mods.Count(item => item.Enabled)} / {mods.Count}" : "Scan required", HasReached(WorkflowState.Scanned) ? AccentGreen : Secondary));
        stack.Children.Add(Line("Apply to game", GameWriteLabel(), HasReached(WorkflowState.RestoreAvailable) ? AccentGreen : HasReached(WorkflowState.Staged) ? AccentAmber : Secondary));
        return Panel(stack);
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
            ("Profile", WorkflowState.ModFamilyChosen),
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
        return ButtonRow(
            Kpi("Total Mods", mods.Count.ToString(), AccentBlue),
            Kpi("Enabled", mods.Count(item => item.Enabled).ToString(), AccentGreen),
            Kpi("Conflicts", conflicts.Count.ToString(), conflicts.Count > 0 ? AccentRed : AccentGreen),
            Kpi("Warnings", warnings.Count.ToString(), warnings.Count > 0 ? AccentAmber : AccentGreen));
    }

    private static ModRow ToModRow(CoreMod mod)
    {
        var safeAction = mod.Enabled
            ? $"{mod.FileCount} files found. Create a plan to inspect destinations."
            : "Disabled mods are excluded from the active plan.";
        var destination = mod.Enabled ? mod.DestinationPreview : "Disabled in active profile";
        return new ModRow(
            mod.Id,
            mod.Enabled,
            mod.Priority,
            mod.Name,
            mod.Family,
            mod.Source,
            mod.Status,
            mod.Warnings,
            mod.Conflicts,
            destination,
            safeAction);
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
        var destination = Stack(
            Text("Destination", 11, SemiBoldWeight, Secondary),
            WrappedPathText(conflict.Destination));

        var kept = Line("Currently kept", conflict.WinningMod, AccentGreen);
        var overwritten = Line("Would overwrite", conflict.LosingMod == "-" ? "No losing mod detected" : conflict.LosingMod, conflict.LosingMod == "-" ? Secondary : AccentRed);
        var participants = Spaced("Mods in this conflict: " + string.Join(", ", conflict.Participants), 12, Secondary);
        var risk = Spaced("Risk: " + conflict.Risk, 12, AccentAmber);
        var sourceStack = Stack(Text("Conflicting source files", 12, SemiBoldWeight, Secondary));
        foreach (var source in conflict.Sources)
        {
            var marker = string.Equals(source.ModName, conflict.WinningMod, StringComparison.OrdinalIgnoreCase) ? "kept" : "overwritten";
            sourceStack.Children.Add(Spaced($"{source.ModName} ({marker}, priority {source.Priority})", 12, marker == "kept" ? AccentGreen : AccentRed));
            sourceStack.Children.Add(WrappedPathText(source.SourcePath));
        }

        var preferWinner = PrimaryButton("Prefer current winner", AccentGreen, async (_, _) => await PreferConflictWinnerAsync(conflict, conflict.WinningMod));
        var preferOverwritten = PrimaryButton("Prefer overwritten mod", AccentAmber, async (_, _) => await PreferConflictWinnerAsync(conflict, conflict.LosingMod));
        preferOverwritten.IsEnabled = conflict.LosingMod != "-";

        return Panel(Stack(
            destination,
            kept,
            overwritten,
            participants,
            risk,
            sourceStack,
            ButtonRow(preferWinner, preferOverwritten)), "#0F1721", "#243141");
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
                PrimaryButton(mod.Enabled ? "Disable mod" : "Enable mod", mod.Enabled ? AccentAmber : AccentGreen, async (_, _) => await SetModEnabledAsync(mod, !mod.Enabled))));
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
        var any = false;
        foreach (var line in lines)
        {
            any = true;
            stack.Children.Add(Spaced("- " + line, 13, Secondary));
        }
        if (!any)
        {
            stack.Children.Add(Spaced(title == "Warnings" ? "No warnings in the latest dry-run plan." : "Nothing to show yet.", 13, Secondary));
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

    private TextBlock WrappedPathText(string value)
    {
        var text = PathText(value);
        text.TextWrapping = TextWrapping.Wrap;
        text.TextTrimming = TextTrimming.None;
        text.Foreground = White;
        text.Margin = new Thickness(0, 4, 0, 0);
        return text;
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

    private bool CanScan() => currentProject != null && HasReached(WorkflowState.ModsFolderSelected) && !isBusy;

    private bool CanCreatePlan() => currentProject != null && HasReached(WorkflowState.Scanned) && !isBusy;

    private bool IsCurrentStep(WorkflowState completeState, WorkflowState unlockState) => !HasReached(completeState) && HasReached(unlockState);

    private bool CanApplyToStaging() => currentProject != null && planReviewManuallyChecked && HasReached(WorkflowState.PlanReviewed) && !HasReached(WorkflowState.Staged) && !isBusy;

    private bool CanPreviewStagingRecords() => currentProject != null && HasReached(WorkflowState.Staged) && !isBusy;

    private string StagingActionLabel() => HasReached(WorkflowState.Staged) ? "Staging complete" : CanApplyToStaging() ? "Apply to staging" : "Apply to staging locked";

    private string GameWriteLabel()
    {
        if (HasReached(WorkflowState.RestoreAvailable)) return "Manifest available";
        if (HasReached(WorkflowState.Staged)) return "Locked for preview";
        return "Locked";
    }

    private string StepStateText(string label, WorkflowState state)
    {
        return label + ": " + (HasReached(state) ? "complete" : "required");
    }

    private string CurrentProjectLine()
    {
        return currentProject == null ? "Project: required" : "Project: " + currentProject.Name;
    }

    private string StagingManifestStatus()
    {
        if (stagingManifest == null)
        {
            return "Staging manifest is not available yet.";
        }

        return $"{stagingManifest.Copied} copied, {stagingManifest.Overwritten} overwritten, {stagingManifest.Skipped} skipped at {stagingManifest.TargetRoot}. Manifest: {ShortPath(stagingManifest.ManifestPath, 90)}";
    }

    private void ResetCoreResults()
    {
        mods.Clear();
        conflicts.Clear();
        warnings.Clear();
        currentPlan = null;
        stagingManifest = null;
        planReviewManuallyChecked = false;
    }

    private void ApplyConflictCountsToMods()
    {
        if (mods.Count == 0)
        {
            return;
        }

        var counts = new Dictionary<string, int>(StringComparer.OrdinalIgnoreCase);
        foreach (var conflict in conflicts)
        {
            counts[conflict.WinningMod] = counts.TryGetValue(conflict.WinningMod, out var winningCount) ? winningCount + 1 : 1;
            if (conflict.LosingMod != "-")
            {
                counts[conflict.LosingMod] = counts.TryGetValue(conflict.LosingMod, out var losingCount) ? losingCount + 1 : 1;
            }
        }

        for (var i = 0; i < mods.Count; i++)
        {
            var count = counts.TryGetValue(mods[i].Name, out var value) ? value : 0;
            mods[i] = mods[i] with
            {
                Conflicts = count,
                Destination = !mods[i].Enabled
                    ? "Disabled in active profile"
                    : count > 0
                        ? "Review conflict list in Plan"
                        : "No destination conflict in latest plan",
                SafeAction = !mods[i].Enabled
                    ? "Disabled mods are excluded from the active plan."
                    : count > 0
                        ? "Review conflict winner before staging."
                        : "Ready for staging after review."
            };
        }
    }

    private static string SuggestedProjectName(string gameFolder)
    {
        if (string.IsNullOrWhiteSpace(gameFolder))
        {
            return "ModForge Project";
        }

        var trimmed = Path.GetFullPath(gameFolder).TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar);
        var name = Path.GetFileName(trimmed);
        return string.IsNullOrWhiteSpace(name) ? "ModForge Project" : name;
    }

    private static ManagedProjectPaths ManagedProjectPathsFor(string gameFolder)
    {
        var projectName = SuggestedProjectName(gameFolder);
        var projectDirectory = Path.Combine(ManagedProjectsRoot(), SafeFolderName(projectName));
        return new ManagedProjectPaths(
            ProjectDirectory: projectDirectory,
            ProjectFile: Path.Combine(projectDirectory, "modforge.project.json"),
            ModsDirectory: Path.Combine(projectDirectory, "Mods"),
            StagingDirectory: Path.Combine(projectDirectory, ".modforge", "staging"));
    }

    private static string ManagedProjectsRoot()
    {
        var documents = Environment.GetFolderPath(Environment.SpecialFolder.MyDocuments);
        if (string.IsNullOrWhiteSpace(documents))
        {
            documents = Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData);
        }
        return Path.Combine(documents, "ModForge Manager", "Projects");
    }

    private static string SafeFolderName(string value)
    {
        var invalid = Path.GetInvalidFileNameChars().ToHashSet();
        var sanitized = new string(value.Select(character => invalid.Contains(character) ? '_' : character).ToArray()).Trim();
        return string.IsNullOrWhiteSpace(sanitized) ? "ModForge Project" : sanitized;
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
            WorkflowState.ModFamilyChosen => "Game profile chosen",
            WorkflowState.GameFolderSelected => "Game folder selected",
            WorkflowState.ModsFolderSelected => "Mods folder selected",
            WorkflowState.Scanned => "Scan complete",
            WorkflowState.PlanReady => "Plan ready",
            WorkflowState.PlanReviewed => "Plan reviewed",
            WorkflowState.Staged => "Staged",
            WorkflowState.GameApplied => "Game applied",
            WorkflowState.RestoreAvailable => "Game manifest available",
            _ => workflowState.ToString()
        };
    }

    private string GetNextAction()
    {
        return workflowState switch
        {
            WorkflowState.NoProject => "Open a project or start Guided Setup.",
            WorkflowState.ProjectOpened => "Choose a game profile.",
            WorkflowState.ModFamilyChosen => "Choose the game folder.",
            WorkflowState.GameFolderSelected => "Create the managed Mods folder.",
            WorkflowState.ModsFolderSelected => "Scan mods.",
            WorkflowState.Scanned => "Create and review the plan.",
            WorkflowState.PlanReady => "Review conflicts and warnings.",
            WorkflowState.PlanReviewed => "Apply to staging.",
            WorkflowState.Staged => "Review the staging manifest. Game apply is locked for this public preview.",
            WorkflowState.RestoreAvailable => "Inspect the latest manifest or staged records.",
            _ => "Inspect the manifest."
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
        SafetyChip.Text = isBusy
            ? "Safe mode: Dry-run first | Python running on user action"
            : "Safe mode: Dry-run first | No startup scan | Python idle";
        StateChip.Text = "State: " + WorkflowLabel();
        StatusText.Text = WorkflowLabel() + " - " + (string.IsNullOrWhiteSpace(statusMessage) ? GetNextAction() : statusMessage);

        OpenProjectButton.IsEnabled = !isBusy;
        ScanButton.IsEnabled = CanScan();
        PlanButton.IsEnabled = CanCreatePlan();
        ApplyButton.IsEnabled = HasReached(WorkflowState.Staged) && !isBusy;
        ApplyButton.Content = HasReached(WorkflowState.RestoreAvailable)
            ? "View latest manifest"
            : HasReached(WorkflowState.Staged)
                ? "View staging result"
                : "Apply to game locked";

        NavMods.Opacity = CanScan() || activePage == "Mods" ? 1.0 : 0.58;
        NavPlan.Opacity = CanCreatePlan() || activePage == "Plan" ? 1.0 : 0.58;
        NavApply.Opacity = HasReached(WorkflowState.PlanReady) || activePage == "Apply & Restore" ? 1.0 : 0.58;
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

    private sealed record ModRow(string Id, bool Enabled, int Priority, string Name, string Family, string Source, string Status, int Warnings, int Conflicts, string Destination, string SafeAction);

    private sealed record ProfileOption(
        string Id,
        string DisplayName,
        string Family,
        string Description,
        string TrustLevel,
        int RuleCount,
        bool IsExperimental)
    {
        public static ProfileOption FromCore(CoreGameProfile profile)
        {
            return new ProfileOption(
                profile.Id,
                profile.DisplayName,
                profile.Family,
                profile.Description,
                profile.TrustLevel,
                profile.RuleCount,
                profile.IsExperimental);
        }
    }

    private sealed record ManagedProjectPaths(
        string ProjectDirectory,
        string ProjectFile,
        string ModsDirectory,
        string StagingDirectory);

    private sealed record ConflictRow(
        string Destination,
        string WinningMod,
        string LosingMod,
        string Risk,
        IReadOnlyList<string> Participants,
        IReadOnlyList<CoreConflictSource> Sources);

    private sealed class WindowSettings
    {
        public int Width { get; set; }

        public int Height { get; set; }
    }
}

