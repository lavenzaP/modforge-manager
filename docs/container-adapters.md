# Container Adapters

Container adapters identify mod package formats and report whether they can be
read by the current build.

Initial adapters:

- `loose_folder`: supported.
- `zip`: supported for safe member listing and staging extraction.
- `godot_pck`: detected, extraction deferred.
- `unreal_pak`: detected, extraction deferred.

Adapters must fail safely and should not mutate source packages.

ZIP safety rules:

- Directory entries are skipped.
- Absolute paths, drive-prefixed paths, and `..` traversal entries are ignored.
- Extraction writes only through the staging deployer safe-destination check.
