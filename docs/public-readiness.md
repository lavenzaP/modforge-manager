# Public Readiness

This checklist describes the minimum state required before making the repository
public.

## Positioning

ModForge Manager is an MVP release-candidate, staging-first Windows mod
manager/toolkit.

- Python CLI/core is the tested backend.
- WinUI 3 is the primary Windows shell candidate with a real Python bridge.
- WPF and tkinter remain fallback/legacy shells.
- WinUI game-folder apply is intentionally locked in the public preview.
- Game apply and restore exist in the Python CLI/core.

Do not describe the project as a full Mod Organizer 2, Vortex, or Nexus Mods
replacement.

## P0 Before Public Visibility

- License wording is intentional and README matches it.
- README states the staging-first public preview scope, with the Korean version
  kept in `README.ko.md`.
- SECURITY.md exists and explains safe reporting.
- CONTRIBUTING.md exists and blocks real game/mod assets.
- CI runs Python unit tests and compile checks.
- Public staging smoke passes.
- Repository content audit finds no real game files, mod archives, generated
  binaries, secrets, crash dumps, or private logs.

## Staging Baseline

The public baseline must prove real staging:

1. Create or load a project.
2. Scan mods.
3. Build a dry-run deployment plan.
4. Apply the winning plan to `project.staging_dir`.
5. Write a staging install manifest.
6. Leave the game folder unchanged.

The WinUI public preview may expose staging but keep game apply locked. That is
an intentional safety boundary, not a missing public requirement.

## Content Audit

Run:

```powershell
git status --short
git ls-files | Select-String -Pattern "\.exe$|\.dll$|\.pak$|\.ucas$|\.utoc$|\.pck$|\.uasset$|\.uexp$|\.dmp$|\.log$|dist/|bin/|obj/|\.venv/"
git grep -n "C:\\Users\\"
git grep -n "D:\\"
git grep -n "token"
git grep -n "secret"
git grep -n "api_key"
git grep -n "password"
```

Synthetic fixtures under `tests/fixtures` may intentionally use small fake
engine-like files. Real payloads must not be committed.

## Not Supported In Public Preview

- Nexus Mods login, API, or downloads.
- Encrypted PAK handling.
- DRM or anti-tamper bypass.
- Arbitrary `.uasset` editing.
- Godot PCK or Unreal archive repacking.
- Virtual filesystem behavior.
- Bundled Python runtime.
- Installer packaging, signing, or auto-update.
