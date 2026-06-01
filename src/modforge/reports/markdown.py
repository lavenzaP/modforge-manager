"""Markdown report rendering."""

from __future__ import annotations

from modforge.core.deployment_plan import DeploymentPlan
from modforge.core.mod_project import ModProject


def render_deployment_report(project: ModProject, plan: DeploymentPlan) -> str:
    lines = [
        f"# Deployment Report: {project.name}",
        "",
        f"- Dry run: `{str(plan.dry_run).lower()}`",
        f"- Operations: `{len(plan.operations)}`",
        f"- Conflicts: `{len(plan.conflicts)}`",
        "",
        "## Conflicts",
        "",
    ]

    if not plan.conflicts:
        lines.append("No conflicts detected.")
    else:
        for conflict in plan.conflicts:
            lines.extend(
                [
                    f"### `{conflict.destination_path}`",
                    "",
                    f"- Mods: {', '.join(conflict.mods)}",
                    f"- Winner: `{conflict.winning_mod}`",
                    "",
                ]
            )

    lines.extend(["", "## Warnings", ""])
    if not plan.warnings:
        lines.append("No warnings.")
    else:
        lines.extend(f"- {warning}" for warning in plan.warnings)

    return "\n".join(lines).rstrip() + "\n"
