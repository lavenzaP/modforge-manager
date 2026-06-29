# ModForge Manager v0.1.2 Preview 1

Download the Windows asset zip, not the source code archive:

```text
ModForge.Manager-v0.1.2-preview.1-win-x64.zip
```

Extract it anywhere and run:

```text
ModForge.Launcher.exe
```

This is a self-contained portable preview. Visual Studio, the .NET SDK, and a
build step are not needed. There is no installer yet, and Windows SmartScreen
may warn because the app is unsigned.

Preview limits:

- No Nexus downloads yet.
- No native installer yet.
- Focused on Unreal package and simple UE4SS/runtime DLL mods.

SHA256 is printed by:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\package_launcher.ps1
```
