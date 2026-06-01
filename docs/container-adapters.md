# Container Adapters

Container adapters identify mod package formats and report whether they can be
read by the current build.

Initial adapters:

- `loose_folder`: supported.
- `zip`: detected, extraction deferred.
- `godot_pck`: detected, extraction deferred.
- `unreal_pak`: detected, extraction deferred.

Adapters must fail safely and should not mutate source packages.
