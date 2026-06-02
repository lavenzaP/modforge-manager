# Security Policy

## Supported Versions

Security and safety reports are currently reviewed for the latest `main` branch
and the latest MVP release-candidate state only.

## Reporting Safety Issues

Please report safety problems with synthetic reproduction steps whenever
possible. Good reports include:

- The command or GUI workflow used.
- Expected versus actual staging destination.
- A fake fixture tree that reproduces the issue.
- Redacted command output.

Do not attach or upload:

- Real game files.
- Real mod archives.
- Generated staging outputs from real projects.
- Crash dumps.
- Logs containing private paths.
- API keys, tokens, passwords, or account data.

If a report needs paths, replace private paths with examples such as
`C:\Path\To\Game`, `C:\Path\To\Mods`, or
`%USERPROFILE%\Documents\ModForge Manager\Projects\<game>`.

## Safety Boundaries

ModForge is dry-run-first and staging-first. Scan and plan operations should not
modify files. Apply-to-staging writes only inside the configured project staging
directory. Game-folder writes require a separate explicit action and are not
enabled in the WinUI public preview.

Do not request help bypassing encryption, DRM, anti-tamper systems, account
gates, or protected game assets.

