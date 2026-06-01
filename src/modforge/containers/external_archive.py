"""External-tool backed archive extraction helpers."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import shutil
import shlex
import subprocess

from modforge.core.paths import as_posix_relative, iter_files


TOOL_IDS = {
    "godot_pck": "godot_pck_tool",
    "unreal_pak": "unreal_pak",
}


@dataclass(frozen=True, slots=True)
class ExtractionResult:
    extracted_path: Path | None = None
    files: list[tuple[str, int]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def extract_archive(
    archive_path: Path,
    container_type: str,
    configured_tools: dict[str, str],
    extraction_root: Path | None,
) -> ExtractionResult:
    tool_id = TOOL_IDS.get(container_type)
    if tool_id is None:
        return ExtractionResult(warnings=[f"No external extractor is registered for {container_type}."])
    raw_tool = configured_tools.get(tool_id, "").strip()
    if not raw_tool:
        return ExtractionResult(warnings=[f"No external tool configured for {container_type}: {tool_id}."])
    if extraction_root is None:
        return ExtractionResult(warnings=[f"No extraction workspace was provided for {archive_path.name}."])

    output_dir = _safe_output_dir(extraction_root, container_type, archive_path)
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    command = _build_extract_command(container_type, raw_tool, archive_path, output_dir)
    if command is None:
        return ExtractionResult(
            warnings=[
                f"External tool command for {tool_id} must contain both "
                "{archive} and {output} placeholders when used as a command template."
            ]
        )

    try:
        completed = subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=120,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        return ExtractionResult(warnings=[f"External extraction failed for {archive_path.name}: {error}"])
    if completed.returncode != 0:
        details = (completed.stderr or completed.stdout or "").strip().splitlines()
        tail = details[-1] if details else f"exit code {completed.returncode}"
        return ExtractionResult(warnings=[f"External extraction failed for {archive_path.name}: {tail}"])

    files = [
        (as_posix_relative(path, output_dir), path.stat().st_size)
        for path in iter_files(output_dir)
    ]
    if not files:
        return ExtractionResult(
            extracted_path=output_dir,
            warnings=[f"External extraction produced no files for {archive_path.name}."],
        )
    return ExtractionResult(extracted_path=output_dir, files=files)


def _build_extract_command(container_type: str, raw_tool: str, archive_path: Path, output_dir: Path) -> list[str] | None:
    archive = str(archive_path)
    output = str(output_dir)
    if "{archive}" in raw_tool or "{output}" in raw_tool:
        if "{archive}" not in raw_tool or "{output}" not in raw_tool:
            return None
        return [
            _strip_quotes(part).replace("{archive}", archive).replace("{output}", output)
            for part in shlex.split(raw_tool, posix=False)
        ]
    if container_type == "unreal_pak":
        return [raw_tool, archive, "-Extract", output]
    return [raw_tool, archive, "--extract", output]


def _safe_output_dir(extraction_root: Path, container_type: str, archive_path: Path) -> Path:
    root = extraction_root.resolve(strict=False)
    archive_id = archive_path.stem.lower().replace(" ", "-")
    output_dir = (root / container_type / archive_id).resolve(strict=False)
    try:
        output_dir.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"Refusing to extract outside workspace: {archive_path}") from exc
    return output_dir


def _strip_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value
