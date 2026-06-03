using System;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;

namespace ModForge.WinUI;

internal sealed class PythonCoreService
{
    private static readonly TimeSpan DefaultTimeout = TimeSpan.FromSeconds(45);
    private readonly string repoRoot;
    private readonly string pythonExecutable;

    public PythonCoreService()
    {
        repoRoot = FindRepoRoot();
        pythonExecutable = Environment.GetEnvironmentVariable("MODFORGE_PYTHON") ?? "python";
    }

    public Task<CoreProject> LoadProjectAsync(string projectFile, CancellationToken cancellationToken = default)
    {
        return RunProjectCommandAsync(projectFile, cancellationToken);
    }

    public async Task<IReadOnlyList<CoreGameProfile>> ListProfilesAsync(CancellationToken cancellationToken = default)
    {
        using var payload = await RunJsonAsync(new[] { "profiles", "--json" }, cancellationToken);
        var profiles = new List<CoreGameProfile>();
        foreach (var item in payload.RootElement.EnumerateArray())
        {
            var id = GetString(item, "id");
            var displayName = GetString(item, "display_name");
            var trustLevel = GetString(item, "trust_level");
            profiles.Add(new CoreGameProfile(
                Id: id,
                DisplayName: string.IsNullOrWhiteSpace(displayName) ? id : displayName,
                Family: GetString(item, "family"),
                Description: GetString(item, "description"),
                TrustLevel: string.IsNullOrWhiteSpace(trustLevel) ? "builtin" : trustLevel,
                RuleCount: GetArrayCount(item, "deployment_rules"),
                IsExperimental: id.Contains("experimental", StringComparison.OrdinalIgnoreCase)
                    || displayName.Contains("Experimental", StringComparison.OrdinalIgnoreCase)));
        }

        return profiles
            .OrderByDescending(item => RecommendedProfileOrder(item.Id))
            .ThenBy(item => item.DisplayName, StringComparer.OrdinalIgnoreCase)
            .ToList();
    }

    public async Task<CoreDoctorReport> RunDoctorAsync(string? projectFile, CancellationToken cancellationToken = default)
    {
        var args = new List<string> { "doctor", "--json" };
        if (!string.IsNullOrWhiteSpace(projectFile))
        {
            args.Add("--project-file");
            args.Add(projectFile);
        }

        using var payload = await RunJsonAsync(args, cancellationToken);
        var root = payload.RootElement;
        var checks = new List<CoreDoctorCheck>();
        if (root.TryGetProperty("checks", out var checkItems) && checkItems.ValueKind == JsonValueKind.Array)
        {
            foreach (var item in checkItems.EnumerateArray())
            {
                checks.Add(new CoreDoctorCheck(
                    Name: GetString(item, "name"),
                    Status: GetString(item, "status"),
                    Message: GetString(item, "message")));
            }
        }

        return new CoreDoctorReport(
            Version: GetString(root, "version"),
            ProjectFile: GetString(root, "project_file"),
            Checks: checks);
    }

    public async Task<IReadOnlyList<CoreToolCheck>> CheckToolsAsync(string projectFile, CancellationToken cancellationToken = default)
    {
        using var payload = await RunJsonAsync(
            new[] { "tools", "check", "--project-file", projectFile, "--json" },
            cancellationToken);
        var checks = new List<CoreToolCheck>();
        foreach (var item in payload.RootElement.EnumerateArray())
        {
            checks.Add(new CoreToolCheck(
                ToolId: GetString(item, "tool_id"),
                Label: GetString(item, "label"),
                Path: GetString(item, "path"),
                Exists: GetBool(item, "exists"),
                Warning: GetString(item, "warning")));
        }

        return checks;
    }

    public async Task<CoreProject> CreateProjectAsync(
        string name,
        string gameRoot,
        string modsDir,
        string stagingDir,
        string profileId,
        string projectFile,
        CancellationToken cancellationToken = default)
    {
        await RunTextAsync(
            new[]
            {
                "project",
                "init",
                "--name",
                name,
                "--game-root",
                gameRoot,
                "--mods-dir",
                modsDir,
                "--staging-dir",
                stagingDir,
                "--profile",
                profileId,
                "--project-file",
                projectFile
            },
            cancellationToken);
        return await RunProjectCommandAsync(projectFile, cancellationToken);
    }

    public async Task<CoreProject> UpdateProjectPathsAsync(
        string projectFile,
        string? gameRoot = null,
        string? modsDir = null,
        string? stagingDir = null,
        CancellationToken cancellationToken = default)
    {
        var args = new List<string>
        {
            "project",
            "set-paths",
            "--project-file",
            projectFile
        };
        if (!string.IsNullOrWhiteSpace(gameRoot))
        {
            args.Add("--game-root");
            args.Add(gameRoot);
        }
        if (!string.IsNullOrWhiteSpace(modsDir))
        {
            args.Add("--mods-dir");
            args.Add(modsDir);
        }
        if (!string.IsNullOrWhiteSpace(stagingDir))
        {
            args.Add("--staging-dir");
            args.Add(stagingDir);
        }

        await RunTextAsync(args, cancellationToken);
        return await RunProjectCommandAsync(projectFile, cancellationToken);
    }

    public async Task<IReadOnlyList<CoreMod>> ScanModsAsync(string projectFile, CancellationToken cancellationToken = default)
    {
        using var payload = await RunJsonAsync(
            new[] { "scan-mods", "--project-file", projectFile, "--json" },
            cancellationToken);
        var mods = new List<CoreMod>();
        foreach (var item in payload.RootElement.EnumerateArray())
        {
            var warnings = GetArrayCount(item, "warnings");
            var enabled = GetBool(item, "enabled");
            var fileCount = GetArrayCount(item, "files");
            mods.Add(new CoreMod(
                Id: GetString(item, "id"),
                Name: GetString(item, "name"),
                Family: FamilyLabel(GetString(item, "detected_type")),
                Source: GetString(item, "path"),
                Enabled: enabled,
                Priority: GetInt(item, "priority"),
                Status: enabled ? warnings > 0 ? "Warn" : "OK" : "Disabled",
                Warnings: warnings,
                Conflicts: 0,
                FileCount: fileCount,
                DestinationPreview: "Create plan for destinations"));
        }

        return mods;
    }

    public async Task<CorePlan> CreatePlanAsync(string projectFile, CancellationToken cancellationToken = default)
    {
        using var payload = await RunJsonAsync(
            new[] { "plan", "--project-file", projectFile, "--json" },
            cancellationToken);
        var root = payload.RootElement;
        var operations = root.GetProperty("operations").EnumerateArray().ToList();
        var conflicts = new List<CoreConflict>();
        foreach (var conflict in root.GetProperty("conflicts").EnumerateArray())
        {
            var mods = conflict.GetProperty("mods").EnumerateArray().Select(item => item.GetString() ?? "").Where(item => item.Length > 0).ToList();
            var winner = GetString(conflict, "winning_mod");
            var loser = mods.FirstOrDefault(item => !string.Equals(item, winner, StringComparison.OrdinalIgnoreCase)) ?? "-";
            var destination = GetString(conflict, "destination_path");
            var sources = operations
                .Where(operation => SameDestination(GetString(operation, "destination_path"), destination))
                .Where(operation => mods.Contains(GetString(operation, "source_mod"), StringComparer.OrdinalIgnoreCase))
                .Select(operation => new CoreConflictSource(
                    ModName: GetString(operation, "source_mod"),
                    SourcePath: GetString(operation, "source_path"),
                    DestinationPath: GetString(operation, "destination_path"),
                    Priority: GetInt(operation, "source_priority")))
                .OrderByDescending(item => item.Priority)
                .ThenBy(item => item.ModName, StringComparer.OrdinalIgnoreCase)
                .ToList();
            conflicts.Add(new CoreConflict(
                Destination: destination,
                WinningMod: winner,
                LosingMod: loser,
                Participants: mods,
                Sources: sources,
                Risk: "Destination overwrite"));
        }

        var warnings = root.GetProperty("warnings").EnumerateArray()
            .Select(item => item.GetString() ?? "")
            .Where(item => item.Length > 0)
            .ToList();
        var conflictDestinations = conflicts.Select(item => item.Destination.Replace('\\', '/').ToLowerInvariant()).ToHashSet();
        var winningOperations = operations.Count(operation =>
        {
            var destination = GetString(operation, "destination_path").Replace('\\', '/').ToLowerInvariant();
            if (!conflictDestinations.Contains(destination))
            {
                return true;
            }

            var matching = conflicts.FirstOrDefault(item => string.Equals(
                item.Destination.Replace('\\', '/'),
                destination,
                StringComparison.OrdinalIgnoreCase));
            return matching == null || string.Equals(GetString(operation, "source_mod"), matching.WinningMod, StringComparison.OrdinalIgnoreCase);
        });

        return new CorePlan(
            Operations: operations.Count,
            WinningOperations: winningOperations,
            Conflicts: conflicts,
            Warnings: warnings,
            DryRun: GetBool(root, "dry_run"));
    }

    public Task SetPriorityAsync(
        string projectFile,
        IReadOnlyList<string> orderedModIds,
        CancellationToken cancellationToken = default)
    {
        if (orderedModIds.Count == 0)
        {
            throw new PythonCoreException("Cannot update priority without scanned mods.");
        }

        var args = new List<string>
        {
            "profile",
            "set-priority",
            "--project-file",
            projectFile
        };
        args.AddRange(orderedModIds);
        return RunTextAsync(args, cancellationToken);
    }

    public Task SetModEnabledAsync(
        string projectFile,
        string modId,
        bool enabled,
        CancellationToken cancellationToken = default)
    {
        if (string.IsNullOrWhiteSpace(modId))
        {
            throw new PythonCoreException("Cannot update a mod without an id.");
        }

        return RunTextAsync(
            new[] { "profile", enabled ? "enable" : "disable", modId, "--project-file", projectFile },
            cancellationToken);
    }

    public async Task<CoreManifest> ApplyStagingAsync(string projectFile, CancellationToken cancellationToken = default)
    {
        var project = await RunProjectCommandAsync(projectFile, cancellationToken);
        using var payload = await RunJsonAsync(
            new[] { "apply-staging", "--project-file", projectFile, "--yes", "--json" },
            cancellationToken);
        var manifest = ParseCoreManifest(payload.RootElement, Path.Combine(project.StagingDir, ".modforge-install-manifest.json"));
        ValidateStagingManifest(project, manifest);
        return manifest;
    }

    public async Task<CoreManifest> LoadStagingManifestAsync(string projectFile, CancellationToken cancellationToken = default)
    {
        var project = await RunProjectCommandAsync(projectFile, cancellationToken);
        var manifestPath = Path.Combine(project.StagingDir, ".modforge-install-manifest.json");
        if (!File.Exists(manifestPath))
        {
            throw new PythonCoreException("No staging manifest was found. Apply to staging first.");
        }

        var json = await File.ReadAllTextAsync(manifestPath, cancellationToken);
        using var payload = JsonDocument.Parse(json);
        var manifest = ParseCoreManifest(payload.RootElement, manifestPath);
        ValidateStagingManifest(project, manifest);
        return manifest;
    }

    public async Task<CoreTranslationInventory> BuildTranslationInventoryAsync(
        string projectFile,
        CancellationToken cancellationToken = default)
    {
        using var payload = await RunJsonAsync(
            new[] { "translation", "inventory", "--project-file", projectFile, "--target", "staging", "--json" },
            cancellationToken);
        var root = payload.RootElement;
        var summary = root.GetProperty("summary");
        var candidates = new List<CoreTranslationCandidate>();
        if (root.TryGetProperty("candidates", out var candidateItems) && candidateItems.ValueKind == JsonValueKind.Array)
        {
            foreach (var item in candidateItems.EnumerateArray())
            {
                candidates.Add(new CoreTranslationCandidate(
                    RelativePath: GetString(item, "relative_path"),
                    Kind: GetString(item, "kind"),
                    Status: GetString(item, "status"),
                    Extractor: GetString(item, "extractor"),
                    Size: GetInt(item, "size"),
                    SourceMod: GetString(item, "source_mod"),
                    Note: GetString(item, "note")));
            }
        }

        var warnings = root.TryGetProperty("warnings", out var warningItems) && warningItems.ValueKind == JsonValueKind.Array
            ? warningItems.EnumerateArray().Select(item => item.GetString() ?? "").Where(item => item.Length > 0).ToList()
            : new List<string>();

        return new CoreTranslationInventory(
            ProjectName: GetString(root, "project_name"),
            ProfileId: GetString(root, "profile_id"),
            Target: GetString(root, "target"),
            Root: GetString(root, "root"),
            ScannedFiles: GetInt(summary, "scanned_files"),
            TotalCandidates: GetInt(summary, "total_candidates"),
            Extractable: GetInt(summary, "extractable"),
            ToolRequired: GetInt(summary, "tool_required"),
            ArchiveNotInspected: GetInt(summary, "archive_not_inspected"),
            BinaryAssets: GetInt(summary, "binary_asset"),
            Review: GetInt(summary, "review"),
            Candidates: candidates,
            Warnings: warnings);
    }

    private async Task<CoreProject> RunProjectCommandAsync(string projectFile, CancellationToken cancellationToken)
    {
        using var payload = await RunJsonAsync(
            new[] { "project", "show", "--project-file", projectFile, "--json" },
            cancellationToken);
        var root = payload.RootElement;
        var profile = root.GetProperty("game_profile");
        return new CoreProject(
            Name: GetString(root, "name"),
            ProjectFile: projectFile,
            GameRoot: GetString(root, "game_root"),
            ModsDir: GetString(root, "mods_dir"),
            StagingDir: GetString(root, "staging_dir"),
            ProfileId: GetString(profile, "id"),
            ProfileName: GetString(profile, "display_name"));
    }

    private async Task<JsonDocument> RunJsonAsync(IReadOnlyList<string> args, CancellationToken cancellationToken)
    {
        var stdout = await RunTextAsync(args, cancellationToken);
        try
        {
            return JsonDocument.Parse(stdout);
        }
        catch (JsonException ex)
        {
            throw new PythonCoreException("Python command did not return valid JSON: " + TrimForStatus(stdout), ex);
        }
    }

    private async Task<string> RunTextAsync(IReadOnlyList<string> args, CancellationToken cancellationToken)
    {
        using var process = new Process();
        process.StartInfo = new ProcessStartInfo
        {
            FileName = pythonExecutable,
            WorkingDirectory = repoRoot,
            UseShellExecute = false,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            CreateNoWindow = true
        };
        process.StartInfo.Environment["PYTHONPATH"] = BuildPythonPath();
        process.StartInfo.ArgumentList.Add("-m");
        process.StartInfo.ArgumentList.Add("modforge");
        foreach (var arg in args)
        {
            process.StartInfo.ArgumentList.Add(arg);
        }

        try
        {
            process.Start();
        }
        catch (Exception ex)
        {
            throw new PythonCoreException("Python could not be started. Set MODFORGE_PYTHON or install Python.", ex);
        }

        var stdoutTask = process.StandardOutput.ReadToEndAsync(cancellationToken);
        var stderrTask = process.StandardError.ReadToEndAsync(cancellationToken);
        var waitTask = process.WaitForExitAsync(cancellationToken);
        var completed = await Task.WhenAny(waitTask, Task.Delay(DefaultTimeout, cancellationToken));
        if (completed != waitTask)
        {
            TryKill(process);
            throw new PythonCoreException("Python command timed out.");
        }

        await waitTask;
        var stdout = await stdoutTask;
        var stderr = await stderrTask;
        if (process.ExitCode != 0)
        {
            var detail = string.IsNullOrWhiteSpace(stderr) ? stdout.Trim() : stderr.Trim();
            throw new PythonCoreException($"Python command failed with exit code {process.ExitCode}: {detail}");
        }

        return stdout;
    }

    private string BuildPythonPath()
    {
        var srcPath = Path.Combine(repoRoot, "src");
        var existing = Environment.GetEnvironmentVariable("PYTHONPATH");
        return string.IsNullOrWhiteSpace(existing) ? srcPath : srcPath + Path.PathSeparator + existing;
    }

    private static string FindRepoRoot()
    {
        foreach (var candidate in Ancestors(AppContext.BaseDirectory).Concat(Ancestors(Environment.CurrentDirectory)))
        {
            if (File.Exists(Path.Combine(candidate, "src", "modforge", "cli.py")))
            {
                return candidate;
            }
        }

        return Environment.CurrentDirectory;
    }

    private static IEnumerable<string> Ancestors(string start)
    {
        var directory = new DirectoryInfo(start);
        while (directory != null)
        {
            yield return directory.FullName;
            directory = directory.Parent;
        }
    }

    private static void TryKill(Process process)
    {
        try
        {
            if (!process.HasExited)
            {
                process.Kill(entireProcessTree: true);
            }
        }
        catch
        {
            // Timeout handling should surface the original timeout, not kill failures.
        }
    }

    private static string FamilyLabel(string detectedType)
    {
        return detectedType switch
        {
            "loose_folder" => "Loose Folder",
            "zip" => "ZIP",
            "godot_pck" => "Godot PCK",
            "unreal_pak" => "Unreal PAK",
            "linked_path" => "Linked Path",
            "" => "Unknown",
            _ => detectedType.Replace("_", " ")
        };
    }

    private static string GetString(JsonElement element, string property)
    {
        return element.TryGetProperty(property, out var value) && value.ValueKind != JsonValueKind.Null
            ? value.ToString()
            : "";
    }

    private static int GetInt(JsonElement element, string property)
    {
        return element.TryGetProperty(property, out var value) && value.TryGetInt32(out var number) ? number : 0;
    }

    private static bool GetBool(JsonElement element, string property)
    {
        return element.TryGetProperty(property, out var value) && value.ValueKind == JsonValueKind.True;
    }

    private static bool SameDestination(string left, string right)
    {
        return string.Equals(
            left.Replace('\\', '/'),
            right.Replace('\\', '/'),
            StringComparison.OrdinalIgnoreCase);
    }

    private static void ValidateStagingManifest(CoreProject project, CoreManifest manifest)
    {
        if (!string.Equals(manifest.Target, "staging", StringComparison.OrdinalIgnoreCase))
        {
            throw new PythonCoreException("Staging apply returned a non-staging manifest. The UI state was not advanced.");
        }

        if (!IsSameOrInside(project.StagingDir, manifest.TargetRoot))
        {
            throw new PythonCoreException("Staging apply returned a target outside the configured project staging folder.");
        }

        if (!IsSameOrInside(project.StagingDir, manifest.ManifestPath))
        {
            throw new PythonCoreException("Staging manifest path is outside the configured project staging folder.");
        }
    }

    private static bool IsSameOrInside(string rootPath, string candidatePath)
    {
        if (string.IsNullOrWhiteSpace(rootPath) || string.IsNullOrWhiteSpace(candidatePath))
        {
            return false;
        }

        var root = Path.GetFullPath(rootPath).TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar);
        var candidate = Path.GetFullPath(candidatePath).TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar);
        return string.Equals(root, candidate, StringComparison.OrdinalIgnoreCase)
            || candidate.StartsWith(root + Path.DirectorySeparatorChar, StringComparison.OrdinalIgnoreCase)
            || candidate.StartsWith(root + Path.AltDirectorySeparatorChar, StringComparison.OrdinalIgnoreCase);
    }

    private static int GetArrayCount(JsonElement element, string property)
    {
        return element.TryGetProperty(property, out var value) && value.ValueKind == JsonValueKind.Array
            ? value.GetArrayLength()
            : 0;
    }

    private static CoreManifest ParseCoreManifest(JsonElement root, string manifestPath)
    {
        var records = new List<CoreManifestRecord>();
        if (root.TryGetProperty("records", out var recordItems) && recordItems.ValueKind == JsonValueKind.Array)
        {
            foreach (var item in recordItems.EnumerateArray())
            {
                records.Add(new CoreManifestRecord(
                    DestinationPath: GetString(item, "destination_path"),
                    SourceMod: GetString(item, "source_mod"),
                    Status: GetString(item, "status"),
                    BackupPath: GetString(item, "backup_path")));
            }
        }

        return new CoreManifest(
            ManifestId: GetString(root, "manifest_id"),
            Target: GetString(root, "target"),
            TargetRoot: GetString(root, "target_root"),
            AppliedAt: GetString(root, "applied_at"),
            Copied: GetArrayCount(root, "copied_files"),
            Overwritten: GetArrayCount(root, "overwritten_files"),
            Skipped: GetArrayCount(root, "skipped_files"),
            ManifestPath: manifestPath,
            Records: records);
    }

    private static int RecommendedProfileOrder(string id)
    {
        return id switch
        {
            "unreal-pak" => 110,
            "stellar-blade.experimental" => 105,
            "mhw-reframework" => 90,
            "sts2-mods" => 80,
            "godot-pck" => 70,
            "generic-folder" => 60,
            _ => 0
        };
    }

    private static string TrimForStatus(string value)
    {
        var trimmed = value.Trim();
        return trimmed.Length <= 500 ? trimmed : trimmed[..500] + "...";
    }
}

internal sealed class PythonCoreException : Exception
{
    public PythonCoreException(string message)
        : base(message)
    {
    }

    public PythonCoreException(string message, Exception innerException)
        : base(message, innerException)
    {
    }
}

internal sealed record CoreProject(
    string Name,
    string ProjectFile,
    string GameRoot,
    string ModsDir,
    string StagingDir,
    string ProfileId,
    string ProfileName);

internal sealed record CoreGameProfile(
    string Id,
    string DisplayName,
    string Family,
    string Description,
    string TrustLevel,
    int RuleCount,
    bool IsExperimental);

internal sealed record CoreDoctorReport(
    string Version,
    string ProjectFile,
    IReadOnlyList<CoreDoctorCheck> Checks);

internal sealed record CoreDoctorCheck(
    string Name,
    string Status,
    string Message);

internal sealed record CoreToolCheck(
    string ToolId,
    string Label,
    string Path,
    bool Exists,
    string Warning);

internal sealed record CoreMod(
    string Id,
    string Name,
    string Family,
    string Source,
    bool Enabled,
    int Priority,
    string Status,
    int Warnings,
    int Conflicts,
    int FileCount,
    string DestinationPreview);

internal sealed record CoreConflict(
    string Destination,
    string WinningMod,
    string LosingMod,
    IReadOnlyList<string> Participants,
    IReadOnlyList<CoreConflictSource> Sources,
    string Risk);

internal sealed record CoreConflictSource(string ModName, string SourcePath, string DestinationPath, int Priority);

internal sealed record CorePlan(
    int Operations,
    int WinningOperations,
    IReadOnlyList<CoreConflict> Conflicts,
    IReadOnlyList<string> Warnings,
    bool DryRun);

internal sealed record CoreManifest(
    string ManifestId,
    string Target,
    string TargetRoot,
    string AppliedAt,
    int Copied,
    int Overwritten,
    int Skipped,
    string ManifestPath,
    IReadOnlyList<CoreManifestRecord> Records);

internal sealed record CoreManifestRecord(
    string DestinationPath,
    string SourceMod,
    string Status,
    string BackupPath);

internal sealed record CoreTranslationInventory(
    string ProjectName,
    string ProfileId,
    string Target,
    string Root,
    int ScannedFiles,
    int TotalCandidates,
    int Extractable,
    int ToolRequired,
    int ArchiveNotInspected,
    int BinaryAssets,
    int Review,
    IReadOnlyList<CoreTranslationCandidate> Candidates,
    IReadOnlyList<string> Warnings);

internal sealed record CoreTranslationCandidate(
    string RelativePath,
    string Kind,
    string Status,
    string Extractor,
    int Size,
    string SourceMod,
    string Note);
