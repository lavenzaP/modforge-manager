using System.Collections.Generic;

namespace ModForge.App
{
    public enum WorkflowState
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

    public sealed class ProjectSnapshot
    {
        public string ProjectName { get; set; }
        public string ProjectPath { get; set; }
        public string ProfileId { get; set; }
        public int TotalMods { get; set; }
        public int EnabledMods { get; set; }
        public int ConflictCount { get; set; }
        public int WarningCount { get; set; }
        public string LastPlanStatus { get; set; }
        public string NextAction { get; set; }
        public IList<ModFamilyInfo> Families { get; set; }
        public IList<SetupStep> Steps { get; set; }
        public IList<ModRow> Mods { get; set; }
        public IList<ConflictRow> Conflicts { get; set; }
        public IList<string> Warnings { get; set; }
        public IList<ToolStatusRow> Tools { get; set; }
        public IList<ManifestRow> Manifests { get; set; }

        public ProjectSnapshot()
        {
            ProjectName = "";
            ProjectPath = "";
            ProfileId = "";
            LastPlanStatus = "";
            NextAction = "";
            Families = new List<ModFamilyInfo>();
            Steps = new List<SetupStep>();
            Mods = new List<ModRow>();
            Conflicts = new List<ConflictRow>();
            Warnings = new List<string>();
            Tools = new List<ToolStatusRow>();
            Manifests = new List<ManifestRow>();
        }
    }

    public sealed class ModFamilyInfo
    {
        public string Name { get; set; }
        public string Summary { get; set; }
        public string SafeWorkflow { get; set; }
        public string Accent { get; set; }

        public ModFamilyInfo(string name, string summary, string safeWorkflow, string accent)
        {
            Name = name;
            Summary = summary;
            SafeWorkflow = safeWorkflow;
            Accent = accent;
        }
    }

    public sealed class SetupStep
    {
        public int Number { get; set; }
        public string Title { get; set; }
        public string Detail { get; set; }
        public bool Done { get; set; }
        public bool Risky { get; set; }

        public SetupStep(int number, string title, string detail, bool done, bool risky)
        {
            Number = number;
            Title = title;
            Detail = detail;
            Done = done;
            Risky = risky;
        }
    }

    public sealed class ModRow
    {
        public bool Enabled { get; set; }
        public int Priority { get; set; }
        public string Name { get; set; }
        public string Type { get; set; }
        public string Source { get; set; }
        public string Status { get; set; }
        public int Warnings { get; set; }
        public int Conflicts { get; set; }
        public string DestinationPaths { get; set; }
        public string SafeAction { get; set; }

        public ModRow(bool enabled, int priority, string name, string type, string source, string status, int warnings, int conflicts)
        {
            Enabled = enabled;
            Priority = priority;
            Name = name;
            Type = type;
            Source = source;
            Status = status;
            Warnings = warnings;
            Conflicts = conflicts;
            DestinationPaths = "";
            SafeAction = "";
        }
    }

    public sealed class ConflictRow
    {
        public string Destination { get; set; }
        public string WinningMod { get; set; }
        public string LosingMod { get; set; }
        public string Risk { get; set; }

        public ConflictRow(string destination, string winningMod, string losingMod, string risk)
        {
            Destination = destination;
            WinningMod = winningMod;
            LosingMod = losingMod;
            Risk = risk;
        }
    }

    public sealed class ToolStatusRow
    {
        public string Name { get; set; }
        public string Status { get; set; }
        public string Detail { get; set; }

        public ToolStatusRow(string name, string status, string detail)
        {
            Name = name;
            Status = status;
            Detail = detail;
        }
    }

    public sealed class ManifestRow
    {
        public string Id { get; set; }
        public string Target { get; set; }
        public string Created { get; set; }
        public string Summary { get; set; }

        public ManifestRow(string id, string target, string created, string summary)
        {
            Id = id;
            Target = target;
            Created = created;
            Summary = summary;
        }
    }

    public sealed class OperationResult
    {
        public bool Ok { get; set; }
        public string Title { get; set; }
        public string Message { get; set; }

        public OperationResult(bool ok, string title, string message)
        {
            Ok = ok;
            Title = title;
            Message = message;
        }
    }
}
