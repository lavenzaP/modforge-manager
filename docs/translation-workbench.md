# Translation Workbench

Translation support is now scoped around the Unreal-first workbench direction.
The first useful surface is read-only inventory of staged output, not archive
repacking or binary asset editing.

## Current Target

- Run `translation inventory --project-file <project> --target staging` after
  staging apply.
- Detect JSON/CSV/TXT files that the current exporter can process.
- Detect Unreal `.locres` and `.locmeta` files as localization resources that
  require a future extractor.
- Detect staged `.pak/.ucas/.utoc` archives as archive artifacts whose internals
  are not inspected yet.
- Detect `.uasset/.uexp/.ubulk` as binary Unreal assets that ModForge does not
  edit.
- Surface the same inventory in the WinUI Apply & Restore page.
- Keep WinUI inventory gated behind a loaded project and completed staging. It
  does not scan arbitrary folders at startup.

## Existing Extractor

- `translation extract --source <folder> --output <csv>` exports JSON/CSV/TXT
  strings into a CSV review file.
- The exporter is intended for loose files or folders that have already been
  extracted by external tooling.
- `translation inventory --source <folder>` is an explicit advanced CLI
  override for inspecting a chosen folder. The default product flow should use
  `--project-file <project> --target staging` so results are tied to the staged
  manifest.

## Deferred

- Unreal `.locres` extraction.
- PO/XLIFF pipelines.
- PCK/PAK repacking.
- `.uasset` editing or binary patching.
- Service-specific machine translation automation.
