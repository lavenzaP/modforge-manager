# Container Adapters

Container adapters identify mod package formats and report whether they can be
read by the current build.

Initial adapters:

- `loose_folder`: supported.
- `zip`: supported for safe member listing and staging extraction.
- `godot_pck`: detected; supported when `godot_pck_tool` is configured.
- `unreal_pak`: detected; supported when `unreal_pak` is configured.

For MVP certification, Godot PCK and Unreal archive packages also support an
archive-as-is deployment path when the external extractor is not configured.
Extractor-backed scans are used for inspection and translation workspaces, while
archive-as-is scans keep installation workflows usable for `.pck`, `.pak`,
`.ucas`, and `.utoc` files.

Adapters must fail safely and should not mutate source packages.

ZIP safety rules:

- Directory entries are skipped.
- Absolute paths, drive-prefixed paths, and `..` traversal entries are ignored.
- Extraction writes only through the staging deployer safe-destination check.

## External Archive Extraction

PCK and PAK packages are extracted through user-configured external tools into
`.modforge/extracted/<container>/<package-id>/`. Source archives are never
modified.

Configured tool values can be either a plain executable path or a command
template containing both `{archive}` and `{output}` placeholders.

Example:

```powershell
python -m modforge.cli tools set unreal_pak "C:\Tools\UnrealPak.exe {archive} -Extract {output}"
```

If a plain UnrealPak path is configured, ModForge calls:

```text
<tool> <archive> -Extract <output>
```

For Godot PCK tools with different command-line syntax, prefer the explicit
template form so the archive and output directory are unambiguous. Failed or
empty extraction creates warnings and does not write to the game folder.

Unreal sidecar sets are checked at scan time. A `.pak/.ucas/.utoc` set with a
missing sidecar produces a warning, but ModForge still treats archive files as
normal manifest-tracked deployment files.
