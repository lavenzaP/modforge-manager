# AGENTS

- Default to Korean for user-facing replies.
- This repo is now a Windows-first C# WinForms launcher.
- Keep the backend inside `desktop/ModForge.Launcher` unless a real need appears.
- Do not reintroduce Python, WinUI, WPF, Rust, or new dependencies without explicit approval.
- Use `scripts\smoke_launcher.ps1` as the default check.
- Never commit real mod/game payloads, crash dumps, DLLs, or EXEs.
- For multi-agent work, follow `docs/agent-pipeline.md`.
- Every UI/import/apply/path change should get the Beginner Gamer Reviewer pass.
- Every write/delete/extract/launch change should get the Safety Reviewer pass.
