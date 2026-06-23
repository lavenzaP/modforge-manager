# Agent Pipeline

This repo uses agents as a development workflow, not as runtime product code.
Keep the app small; make the work reviewable.

## Flow

1. Pick one task from `TODO.md` or a user report.
2. Write a short goal:
   - user-visible problem
   - files likely to change
   - what is out of scope
3. Run the useful agents only:
   - Planner
   - Implementer
   - Beginner Gamer Reviewer
   - Safety Reviewer
   - Verifier
   - Release Agent, only for release work
4. Merge the feedback into the smallest working change.
5. Record the checks that passed.

## Agent Goals

### Planner

```text
/goal Turn this request into one small ModForge Manager task.
Define scope, files to touch, user impact, safety risk, and what not to do.
Do not add dependencies or new frameworks.
```

### Implementer

```text
/goal Implement the approved task in the smallest safe diff.
Prefer desktop/ModForge.Launcher/Program.cs.
Do not reintroduce Python, WPF, WinUI, Rust, or new dependencies.
Do not commit real game or mod files.
```

### Beginner Gamer Reviewer

```text
/goal Review this change as a user who only wants to install mods and play.
Flag confusing labels, hidden steps, unclear apply/remove behavior, scary errors,
and anything that assumes modding knowledge.
```

Use this reviewer for every UI, import, apply, remove, path, or release change.

Checklist:

- Can a normal gamer understand this without knowing Unreal, `.pak`, manifests,
  hashes, DLLs, symlinks, or game folder layouts?
- Does each action make clear whether it changes the ModForge library, the real
  game folder, or both?
- Before anything touches the game folder, can the user see which game, which
  folder, and which files will change?
- If something is blocked, does the message explain the safe next step instead
  of showing a raw technical error?
- Can the user answer: what will change, can I undo it, and what should I do if
  it fails?

### Safety Reviewer

```text
/goal Review this change for game-file safety.
Check apply/remove, manifests, backups, archive extraction, path traversal,
hash checks, and accidental commits of game/mod payloads.
```

Use this reviewer for every change that can write, delete, extract, or launch.

Checklist:

- Game-folder writes must stay inside the selected game root.
- Apply/remove must keep the manifest and backup path intact.
- If an applied file changed outside ModForge, the app must stop instead of
  overwriting or deleting it silently.
- Archive import must reject path traversal and unsafe extracted paths.
- Changes must not commit real payloads: `.exe`, `.dll`, `.pak`, `.ucas`,
  `.utoc`, `.zip`, `.rar`, `.7z`, crash dumps, or real game files.

### Verifier

```text
/goal Verify the branch and report exact commands and results.
Run the default checks and inspect git status.
```

Required local checks:

```powershell
dotnet build desktop\ModForge.Launcher\ModForge.Launcher.csproj --configuration Release
dotnet run --project desktop\ModForge.Launcher\ModForge.Launcher.csproj -- --self-test
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\smoke_launcher.ps1
git diff --check
git status -sb
```

Payload check:

```powershell
$payloads = git ls-files | Where-Object { $_ -match '(?i)(^|/)(dist|build|\.modforge|bin|obj)/|\.(zip|rar|7z|pak|ucas|utoc|pck|uasset|uexp|dll|exe|mdmp|dmp)$' }
if ($payloads) { $payloads; exit 1 }
```

### Release Agent

```text
/goal Prepare a prerelease only after main CI is green.
Build the portable zip, upload it as a GitHub prerelease, and report SHA256.
```

Use preview tags until the app has an installer and a stable apply/restore UI:

```text
v0.x.x-preview.x
```

Before a release:

- Target only a `main` commit whose GitHub Actions `CI` passed.
- Rebuild the portable zip; do not reuse an old `dist` asset.
- Check tag conflicts before creating the release.
- Verify the uploaded asset and report SHA256.

## Hard Rules

- Keep launcher-owned data beside `ModForge.Launcher.exe`.
- Keep production code in `desktop/ModForge.Launcher` unless there is a real need.
- Do not add runtime AI or background agents to the app.
- Do not add dependencies for process management, templating, or task tracking.
- Do not commit `.exe`, `.dll`, `.pak`, `.ucas`, `.utoc`, `.zip`, `.rar`, `.7z`,
  crash dumps, or real game files.
