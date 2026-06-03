"""Read-only translation inventory for staged mod output."""

from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path


TRANSLATION_HINTS = (
    "localization",
    "localisation",
    "locale",
    "locres",
    "l10n",
    "i18n",
    "strings",
    "stringtable",
    "dialog",
    "dialogue",
    "subtitle",
    "subtitles",
    "text",
)


@dataclass(frozen=True, slots=True)
class TranslationInventoryCandidate:
    relative_path: str
    kind: str
    status: str
    extractor: str
    size: int
    source_mod: str = ""
    note: str = ""

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class TranslationInventoryReport:
    project_name: str
    profile_id: str
    profile_family: str
    target: str
    root: str
    exists: bool
    scanned_files: int
    candidates: list[TranslationInventoryCandidate]
    warnings: list[str]

    def summary(self) -> dict[str, int]:
        statuses = {
            "extractable": 0,
            "tool_required": 0,
            "archive_not_inspected": 0,
            "binary_asset": 0,
            "review": 0,
        }
        unreal_localization = 0
        for candidate in self.candidates:
            if candidate.status in statuses:
                statuses[candidate.status] += 1
            if candidate.kind in {"unreal_locres", "unreal_locmeta"}:
                unreal_localization += 1
        return {
            "scanned_files": self.scanned_files,
            "total_candidates": len(self.candidates),
            "unreal_localization": unreal_localization,
            **statuses,
        }

    def to_dict(self) -> dict[str, object]:
        return {
            "project_name": self.project_name,
            "profile_id": self.profile_id,
            "profile_family": self.profile_family,
            "target": self.target,
            "root": self.root,
            "exists": self.exists,
            "scanned_files": self.scanned_files,
            "summary": self.summary(),
            "candidates": [candidate.to_dict() for candidate in self.candidates],
            "warnings": self.warnings,
        }


def build_translation_inventory(
    root: Path,
    *,
    project_name: str = "",
    profile_id: str = "",
    profile_family: str = "",
    target: str = "staging",
) -> TranslationInventoryReport:
    scan_root = root.resolve(strict=False)
    if not scan_root.exists():
        return TranslationInventoryReport(
            project_name=project_name,
            profile_id=profile_id,
            profile_family=profile_family,
            target=target,
            root=str(scan_root),
            exists=False,
            scanned_files=0,
            candidates=[],
            warnings=[f"Inventory root does not exist: {scan_root}"],
        )

    source_mods = _load_staging_sources(scan_root)
    candidates: list[TranslationInventoryCandidate] = []
    scanned_files = 0
    warnings: list[str] = []

    for path in sorted(scan_root.rglob("*"), key=lambda item: item.as_posix().lower()):
        if not path.is_file():
            continue
        relative_path = path.relative_to(scan_root).as_posix()
        if _is_internal_file(relative_path):
            continue
        scanned_files += 1
        candidate = _classify_candidate(relative_path, path.stat().st_size, source_mods)
        if candidate is not None:
            candidates.append(candidate)

    if not candidates and scanned_files:
        warnings.append("No translation-like files were detected in the selected output.")
    if any(candidate.status == "archive_not_inspected" for candidate in candidates):
        warnings.append(
            "Unreal archives are listed as staged artifacts only; internal strings require an extraction tool first."
        )
    if any(candidate.kind in {"unreal_locres", "unreal_locmeta"} for candidate in candidates):
        warnings.append("Unreal localization resources were detected but are not extracted by the built-in CSV exporter yet.")

    return TranslationInventoryReport(
        project_name=project_name,
        profile_id=profile_id,
        profile_family=profile_family,
        target=target,
        root=str(scan_root),
        exists=True,
        scanned_files=scanned_files,
        candidates=candidates,
        warnings=warnings,
    )


def format_translation_inventory(report: TranslationInventoryReport) -> str:
    summary = report.summary()
    lines = [
        f"Translation inventory: {report.project_name or report.target}",
        f"Target: {report.target}",
        f"Root: {report.root}",
        f"Scanned files: {summary['scanned_files']}",
        f"Candidates: {summary['total_candidates']}",
        f"Extractable now: {summary['extractable']}",
        f"Tool required: {summary['tool_required']}",
        f"Archives not inspected: {summary['archive_not_inspected']}",
        f"Binary assets: {summary['binary_asset']}",
    ]
    for warning in report.warnings:
        lines.append(f"WARNING: {warning}")
    for candidate in report.candidates:
        source = f" [{candidate.source_mod}]" if candidate.source_mod else ""
        lines.append(f"- {candidate.relative_path}{source}: {candidate.status} ({candidate.kind})")
    return "\n".join(lines)


def _classify_candidate(
    relative_path: str,
    size: int,
    source_mods: dict[str, str],
) -> TranslationInventoryCandidate | None:
    normalized = relative_path.replace("\\", "/")
    lower = normalized.casefold()
    suffix = Path(normalized).suffix.casefold()
    source_mod = source_mods.get(lower, "")

    if suffix == ".json":
        return _candidate(normalized, "json_strings", "extractable", "json", size, source_mod, "Ready for CSV export.")
    if suffix == ".csv":
        return _candidate(normalized, "csv_strings", "extractable", "csv", size, source_mod, "Ready for CSV review.")
    if suffix == ".txt":
        return _candidate(normalized, "text_strings", "extractable", "txt", size, source_mod, "Plain text can be exported.")
    if suffix in {".locres"}:
        return _candidate(
            normalized,
            "unreal_locres",
            "tool_required",
            "",
            size,
            source_mod,
            "Unreal .locres detected; extraction support is intentionally deferred.",
        )
    if suffix in {".locmeta"}:
        return _candidate(
            normalized,
            "unreal_locmeta",
            "tool_required",
            "",
            size,
            source_mod,
            "Unreal localization metadata detected.",
        )
    if suffix in {".pak", ".ucas", ".utoc"}:
        return _candidate(
            normalized,
            "unreal_archive",
            "archive_not_inspected",
            "",
            size,
            source_mod,
            "Staged Unreal archive; internal localization is not visible until extraction.",
        )
    if suffix in {".uasset", ".uexp", ".ubulk"}:
        return _candidate(
            normalized,
            "unreal_binary_asset",
            "binary_asset",
            "",
            size,
            source_mod,
            "Binary Unreal asset; direct text extraction is not supported.",
        )
    if suffix in {".ini", ".cfg", ".yaml", ".yml", ".toml", ".xml"} and _looks_translation_related(lower):
        return _candidate(
            normalized,
            "text_config",
            "review",
            "",
            size,
            source_mod,
            "Looks translation-related, but no built-in extractor is assigned.",
        )
    if _looks_translation_related(lower):
        return _candidate(
            normalized,
            "translation_like_file",
            "review",
            "",
            size,
            source_mod,
            "Path looks translation-related; inspect manually.",
        )
    return None


def _candidate(
    relative_path: str,
    kind: str,
    status: str,
    extractor: str,
    size: int,
    source_mod: str,
    note: str,
) -> TranslationInventoryCandidate:
    return TranslationInventoryCandidate(
        relative_path=relative_path,
        kind=kind,
        status=status,
        extractor=extractor,
        size=size,
        source_mod=source_mod,
        note=note,
    )


def _looks_translation_related(path: str) -> bool:
    return any(hint in path for hint in TRANSLATION_HINTS)


def _is_internal_file(relative_path: str) -> bool:
    normalized = relative_path.replace("\\", "/")
    return normalized == ".modforge-install-manifest.json" or normalized.startswith(".modforge/")


def _load_staging_sources(root: Path) -> dict[str, str]:
    manifest_path = root / ".modforge-install-manifest.json"
    if not manifest_path.exists():
        return {}
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    records = payload.get("records", [])
    if not isinstance(records, list):
        return {}
    sources: dict[str, str] = {}
    for record in records:
        if not isinstance(record, dict):
            continue
        destination = str(record.get("destination_path", "")).replace("\\", "/").casefold()
        source_mod = str(record.get("source_mod", ""))
        if destination and source_mod:
            sources[destination] = source_mod
    return sources
