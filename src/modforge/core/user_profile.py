"""User profile model for enabled mods and priority order."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True)
class UserProfile:
    id: str = "default"
    name: str = "Default"
    disabled_mod_ids: list[str] = field(default_factory=list)
    mod_priority_order: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, value: dict[str, object]) -> "UserProfile":
        return cls(
            id=str(value.get("id", "default")),
            name=str(value.get("name", "Default")),
            disabled_mod_ids=list(value.get("disabled_mod_ids", [])),  # type: ignore[arg-type]
            mod_priority_order=list(value.get("mod_priority_order", [])),  # type: ignore[arg-type]
        )

    def is_enabled(self, mod_id: str) -> bool:
        return mod_id not in set(self.disabled_mod_ids)

    def priority_for(self, mod_id: str, default_priority: int) -> int:
        if mod_id in self.mod_priority_order:
            return self.mod_priority_order.index(mod_id)
        return len(self.mod_priority_order) + default_priority

    def set_enabled(self, mod_id: str, enabled: bool) -> None:
        disabled = [item for item in self.disabled_mod_ids if item != mod_id]
        if not enabled:
            disabled.append(mod_id)
        self.disabled_mod_ids = disabled

    def set_priority_order(self, ordered_mod_ids: list[str]) -> None:
        deduped: list[str] = []
        for mod_id in ordered_mod_ids:
            if mod_id and mod_id not in deduped:
                deduped.append(mod_id)
        self.mod_priority_order = deduped

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "name": self.name,
            "disabled_mod_ids": self.disabled_mod_ids,
            "mod_priority_order": self.mod_priority_order,
        }
