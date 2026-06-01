# Architecture V2

Milestone 6A moves ModForge Manager toward a Windows-first desktop product
without throwing away the tested Python core.

## Goal

Provide a fast `.exe` shell that teaches the safe mod workflow on launch, then
delegates real scan, plan, apply, restore, and translation work to proven core
components only when the user asks.

## Current Baseline

- Python core and CLI are the source of truth for scan, plan, conflict, apply,
  manifest, restore, audit, and translation behavior.
- The tkinter GUI remains useful as a lightweight debug/fallback shell.
- PySide6 is optional and remains an experiment, not the Windows product shell.

## Decision: WPF Shell

The new default Windows experience is a C# WPF shell under
`desktop/ModForge.App`.

WPF owns:

- first-run onboarding;
- navigation and modern desktop layout;
- progress, cancellation, and user-friendly error display;
- safe action prompts and restore visibility;
- `.exe`-first local execution.

WPF does not reimplement:

- mod scanning;
- deployment planning;
- apply/restore safety rules;
- archive extraction;
- translation extraction.

## Decision: Python Sidecar

Python remains the source of truth for core behavior. The WPF shell will call it
through a lazy sidecar contract in a later milestone.

Milestone 6A includes only:

- `IPythonSidecarService`;
- `FakePythonSidecarService`;
- demo project data;
- a visible sidecar check button that proves no Python process runs at startup.

The future bridge should use compact JSON request/response messages and
structured errors. Initial transport can be process invocation or stdio; HTTP or
gRPC should wait until there is a concrete reason.

## Decision: Rust Later

Rust is reserved for measured hot paths, not for the first WPF shell.

Candidate areas:

- very large directory scans;
- checksum/index creation;
- path normalization batches;
- archive metadata probing;
- conflict graph acceleration.

Rust should attach as a helper binary or Python acceleration layer without
breaking the WPF-to-sidecar contract.

## Decision: tkinter Legacy Policy

The tkinter UI stays available as `modforge-gui` and `run_gui.bat`.

Policy:

- keep smoke tests and critical safety fixes;
- do not build new product UX there;
- prefer WPF for onboarding and future rich UI work.

## Startup Contract

Cold start must not run:

- Python sidecar probing;
- mod folder scanning;
- external tool checks;
- PCK/PAK probing;
- hash calculation;
- full doctor checks.

Cold start may load:

- WPF resources;
- cached or demo project metadata;
- onboarding copy;
- local UI state.

## Milestone 6A Done Criteria

- WPF shell launches as an `.exe`.
- It runs without Python.
- It shows a guided setup path for REFramework, Unreal, and Godot/STS2 mods.
- It displays demo Home, Mods, Plan, Apply/Restore, and Tools screens.
- It proves sidecar probing is lazy.
- Existing Python tests remain green.
