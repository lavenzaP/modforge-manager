using System.Threading;
using System.Threading.Tasks;

namespace ModForge.App
{
    public interface IPythonSidecarService
    {
        bool HasProbed { get; }

        ProjectSnapshot CreateInitialSnapshot();

        Task<OperationResult> ProbeAsync(CancellationToken cancellationToken);
    }

    public sealed class ShellPythonSidecarService : IPythonSidecarService
    {
        private bool hasProbed;

        public bool HasProbed
        {
            get { return hasProbed; }
        }

        public ProjectSnapshot CreateInitialSnapshot()
        {
            var snapshot = new ProjectSnapshot();
            snapshot.ProjectName = "Wilds Project";
            snapshot.ProjectPath = @"C:\Path\To\ModForge\Projects\Wilds Project\project.mfproj";
            snapshot.ProfileId = "mhw-reframework";
            snapshot.TotalMods = 24;
            snapshot.EnabledMods = 16;
            snapshot.ConflictCount = 5;
            snapshot.WarningCount = 3;
            snapshot.LastPlanStatus = "Review required";
            snapshot.NextAction = "Start Guided Setup";

            snapshot.Families.Add(new ModFamilyInfo(
                "REFramework",
                "Loose nativePC and REFramework folders for RE Engine games.",
                "Scan loose files, review destination conflicts, stage first, then apply to game with manifest backups.",
                "#4F9CFF"));
            snapshot.Families.Add(new ModFamilyInfo(
                "Unreal Mods",
                "Pak, UCAS, UTOC, and sidecar files usually placed under a ~mods directory.",
                "Keep archives intact by default, detect same-destination archive conflicts, and avoid encrypted asset promises.",
                "#C47CFF"));
            snapshot.Families.Add(new ModFamilyInfo(
                "Godot / STS2",
                "PCK mods and loose mods-folder layouts for Slay the Spire 2 style workflows.",
                "Treat PCK archives as deployable units, use optional extraction only for inspection and translation workflows.",
                "#3ECF8E"));

            snapshot.Steps.Add(new SetupStep(1, "Choose mod family", "Pick REFramework, Unreal, or Godot/STS2 so ModForge can explain the safe path.", true, false));
            snapshot.Steps.Add(new SetupStep(2, "Select game folder", "Point to the actual game root. No write happens while selecting.", false, false));
            snapshot.Steps.Add(new SetupStep(3, "Select mods folder", "Choose the folder or archive collection you want ModForge to manage.", false, false));
            snapshot.Steps.Add(new SetupStep(4, "Scan mods", "This is the first potentially slow step. It only runs when you press Scan.", false, false));
            snapshot.Steps.Add(new SetupStep(5, "Review plan and conflicts", "Check winners, overwritten destinations, and warnings before any deployment.", false, true));
            snapshot.Steps.Add(new SetupStep(6, "Apply to staging", "Copy to a staging folder first. This is the safest apply path.", false, false));
            snapshot.Steps.Add(new SetupStep(7, "Apply to game", "Requires confirmation and creates backups plus a restore manifest.", false, true));

            snapshot.Mods.Add(Mod(true, 1, "Better UI", "REFramework", @"Mods\BetterUI", "OK", 0, 1, @"reframework\data\ui\betterui.lua", "Review conflict in Plan before staging."));
            snapshot.Mods.Add(Mod(true, 2, "Weapon Texture Pack", "Unreal Pak", "WeaponTX_Pack.zip", "OK", 1, 2, @"Content\Paks\~mods\WeaponTX_Pack.pak", "Keep archive intact and stage first."));
            snapshot.Mods.Add(Mod(true, 3, "REFramework Loader", "REFramework", @"Mods\REFramework", "OK", 0, 0, @"reframework\d2d\reframework.dll", "Ready for staging."));
            snapshot.Mods.Add(Mod(true, 4, "Unreal HD HUD", "Unreal Pak", "HDHUD_v2.zip", "Warn", 1, 1, @"Content\Paks\~mods\HDHUD_v2.pak", "Check warning before staging."));
            snapshot.Mods.Add(Mod(false, 5, "Monster Weakness Icon", "REFramework", @"Mods\WeaknessIcon", "Disabled", 0, 0, @"reframework\data\ui\icons.dds", "Enable only after conflict review."));
            snapshot.Mods.Add(Mod(true, 6, "STS2 Localization EN", "Godot PCK", "Localization_EN.pck", "OK", 0, 0, @"mods\Localization_EN.pck", "Ready for staging."));

            snapshot.Conflicts.Add(new ConflictRow(@"reframework\data\ui\betterui.lua", "Better UI", "Monster Weakness Icon", "Destination overwrite"));
            snapshot.Conflicts.Add(new ConflictRow(@"Content\Paks\~mods\WeaponTX_Pack.pak", "Weapon Texture Pack", "HD Monster Textures", "Archive destination"));
            snapshot.Conflicts.Add(new ConflictRow(@"reframework\data\ui\config.ini", "Better UI", "Unreal HD HUD", "Case-insensitive path match"));

            snapshot.Warnings.Add("WeaponTX_Pack.zip has no preview image. This does not block staging.");
            snapshot.Warnings.Add("HDHUD_v2.zip duplicates one destination already used by another mod.");
            snapshot.Warnings.Add("Unreal sidecar archives must be restored as a set.");

            snapshot.Tools.Add(new ToolStatusRow("7-Zip", "Not configured", "Optional. Used for archive inspection."));
            snapshot.Tools.Add(new ToolStatusRow("UnrealPak", "Not configured", "Optional. Required only for extraction, not archive-as-is deployment."));
            snapshot.Tools.Add(new ToolStatusRow("Godot PCK Tool", "Not configured", "Optional. Used for PCK inspection and translation workflows."));
            snapshot.Tools.Add(new ToolStatusRow("Python Sidecar", "Idle", "No Python process is launched until you ask for a scan or check."));

            return snapshot;
        }

        private static ModRow Mod(bool enabled, int priority, string name, string type, string source, string status, int warnings, int conflicts, string destinationPaths, string safeAction)
        {
            var row = new ModRow(enabled, priority, name, type, source, status, warnings, conflicts);
            row.DestinationPaths = destinationPaths;
            row.SafeAction = safeAction;
            return row;
        }

        public async Task<OperationResult> ProbeAsync(CancellationToken cancellationToken)
        {
            hasProbed = true;
            await Task.Delay(180, cancellationToken);
            return new OperationResult(
                true,
                "Python sidecar idle",
                "No Python process was launched at startup. The real sidecar will start only after a user action.");
        }
    }
}
