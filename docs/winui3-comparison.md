# WinUI 3 Shell Candidate

This repo includes a WinUI 3 shell under `desktop\ModForge.WinUI`. As of
Milestone 6D, WinUI 3 is the primary Windows shell candidate while WPF remains
the fallback until packaging is proven.

- `NavigationView` for the left navigation.
- WinUI `Button`, `CheckBox`, `ListView`, `Border`, and typography spacing.
- `ListView` row layouts instead of WPF `DataGrid`.
- The same safe workflow gating used by the WPF shell:
  `NoProject`, `ProjectOpened`, `ModFamilyChosen`, `GameFolderSelected`,
  `ModsFolderSelected`, `Scanned`, `PlanReady`, `PlanReviewed`, `Staged`,
  `RestoreAvailable`.

## Build

WinUI 3 requires .NET SDK tooling and the Windows App SDK NuGet package.
This machine has been verified with .NET SDK `9.0.314`.

```powershell
winget install --id Microsoft.DotNet.SDK.9 --source winget
powershell -ExecutionPolicy Bypass -File scripts\build_winui_shell.ps1
```

The build script keeps first-run `.NET` state and NuGet packages inside the
repo-local `.dotnet_cli_home` and `.nuget` folders so normal repo builds do not
depend on writable user-profile cache paths.

The project references:

```xml
<PackageReference Include="Microsoft.WindowsAppSDK" Version="1.8.260508005" />
```

That version is from the official NuGet package listing. Windows App SDK 1.8
also changed packaging behavior so the package acts as a metapackage with
component dependencies, which is why restore is required.

## Difference From The WPF Shell

WPF is easier for this repo right now because the current WPF shell can be
compiled with the existing Visual Studio Roslyn compiler and .NET Framework/WPF
references. It does not need project restore.

WinUI 3 is more modern visually and closer to native Windows 11 app patterns,
but it has more toolchain weight:

- requires .NET SDK plus Windows App SDK restore;
- uses different XAML controls and layout defaults;
- does not include a built-in WPF-style `DataGrid`;
- often benefits from Microsoft Community Toolkit controls for richer tables;
- has better Fluent-native controls such as `NavigationView`;
- is a stronger long-term fit if the app will target Windows 11 first.

For ModForge Manager, WinUI 3 is now the preferred Windows UX direction. WPF
remains the fallback because it has a simpler local build path and does not
depend on Windows App SDK restore.

Current executable:

```text
dist\ModForge.WinUI\ModForge.WinUI.exe
```
