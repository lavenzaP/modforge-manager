# Release Checklist

Run before publishing a preview release:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\smoke_launcher.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\package_launcher.ps1
```

Check:

- `dist\ModForge.Manager-v0.1.2-preview.1-win-x64.zip` exists.
- The zip contains `ModForge.Launcher.exe`, `START_HERE.txt`, `README.md`,
  `README.ko.md`, and `LICENSE.txt`.
- Extract the zip to a fresh folder and launch `ModForge.Launcher.exe`.
- Confirm a beginner can find the release asset without using source code.
- Confirm the release notes mention preview limits: no installer, no Nexus
  downloads, Unreal/UE4SS-focused.
