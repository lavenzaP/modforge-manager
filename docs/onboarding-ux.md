# Onboarding UX

The first screen should answer one question: "What should I do next?"

## First-Run Principle

Do not open on a dense admin dashboard. Open on a guided safe action.

The user should immediately see:

- the current project or demo project;
- the next safe action;
- why nothing slow happened at startup;
- the three supported core mod families;
- how restore will work before game writes happen.

## Core Mod Families

### REFramework

For loose RE Engine and `nativePC` style mods.

Safe path:

1. select game root;
2. select mods folder;
3. scan loose destinations;
4. review conflicts;
5. apply to staging;
6. apply to game with manifest backups.

### Unreal Mods

For `~mods`, `.pak`, `.ucas`, and `.utoc` archive workflows.

Safe path:

1. keep archives intact by default;
2. detect archive destination conflicts;
3. warn about unsupported encrypted or arbitrary asset editing cases;
4. stage first;
5. apply with manifest backups.

### Godot / STS2

For `.pck` mods and Slay the Spire 2 style mods-folder layouts.

Safe path:

1. treat PCK as a deployable unit by default;
2. use optional extraction for inspection and translation workflows;
3. review duplicates;
4. stage first;
5. apply with restore manifest.

## Guided Setup Steps

1. Choose mod family.
2. Select game folder.
3. Select mods folder.
4. Scan mods.
5. Review plan and conflicts.
6. Apply to staging.
7. Apply to game.
8. Confirm restore path.

## Screen Tone

Keep the app dense enough for mod management, but avoid a wall of boxes.

Prefer:

- one clear next action;
- grouped workflow lanes;
- subtle panels;
- readable table density;
- visible restore and dry-run state.

Avoid:

- marketing hero pages;
- card grids for every feature;
- automatic scans on launch;
- hidden destructive actions.
