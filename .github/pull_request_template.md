## Summary

- 

## Agent Checks

- [ ] Planner scope stayed small
- [ ] Beginner Gamer Reviewer checked the user flow
- [ ] Safety Reviewer checked file writes/removes/extracts if relevant
- [ ] Release Agent checked packaging only if this is a release

## Verification

- [ ] `dotnet build desktop\ModForge.Launcher\ModForge.Launcher.csproj --configuration Release`
- [ ] `dotnet run --project desktop\ModForge.Launcher\ModForge.Launcher.csproj -- --self-test`
- [ ] `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\smoke_launcher.ps1`
- [ ] `git diff --check`
- [ ] `git status --short`

## Safety

- [ ] No real game/mod payloads, binaries, archives, or crash dumps committed
- [ ] User-owned game files are only changed through the manifest/backup path
