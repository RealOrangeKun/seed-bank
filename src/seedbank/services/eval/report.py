"""Markdown report renderer for offline evaluations.

Produced by the experiment worker after a run completes, uploaded to
``seedbank-experiments/experiments/{experiment_id}/report.md``. The shape is
intentionally human-first: someone landing on the report object without a UI
should be able to see what model+dataset was evaluated and what came out.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID


def render_report(
    *,
    experiment_id: UUID,
    experiment_name: str,
    model_id: UUID,
    model_name: str,
    model_version: str,
    dataset_id: UUID,
    dataset_name: str,
    kind: str,
    summary: dict[str, Any],
    started_at: datetime | None,
    finished_at: datetime | None,
    duration_ms: int | None,
    items_evaluated: int,
    items_failed: int,
) -> str:
    """Render a Markdown report for one experiment run.

    Returned bytes are encoded as UTF-8 by the caller before MinIO upload.
    """
    lines: list[str] = []
    lines.append(f"# Experiment {experiment_name}")
    lines.append("")
    lines.append("| Field | Value |")
    lines.append("|---|---|")
    lines.append(f"| Experiment ID | `{experiment_id}` |")
    lines.append(f"| Kind | `{kind}` |")
    lines.append(f"| Model | `{model_name}` `{model_version}` (`{model_id}`) |")
    lines.append(f"| Dataset | `{dataset_name}` (`{dataset_id}`) |")
    lines.append(f"| Started at | `{_fmt(started_at)}` |")
    lines.append(f"| Finished at | `{_fmt(finished_at)}` |")
    lines.append(f"| Duration (ms) | `{duration_ms if duration_ms is not None else 'n/a'}` |")
    lines.append(f"| Items evaluated | `{items_evaluated}` |")
    lines.append(f"| Items failed | `{items_failed}` |")
    lines.append("")

    lines.append("## Summary metrics")
    lines.append("")
    lines.append("| Metric | Value |")
    lines.append("|---|---|")
    for key, value in _flatten(summary).items():
        lines.append(f"| `{key}` | {_fmt_value(value)} |")
    lines.append("")

    if "confusion" in summary and isinstance(summary["confusion"], dict):
        lines.append("## Confusion matrix")
        lines.append("")
        lines.append("| GT \\ Pred | good | bad |")
        lines.append("|---|---|---|")
        cm: dict[str, int] = summary["confusion"]
        lines.append(f"| **good** | {cm.get('good_pred_good', 0)} | {cm.get('good_pred_bad', 0)} |")
        lines.append(f"| **bad** | {cm.get('bad_pred_good', 0)} | {cm.get('bad_pred_bad', 0)} |")
        lines.append("")

    return "\n".join(lines)


def _flatten(summary: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in summary.items():
        if isinstance(v, dict):
            continue  # confusion gets its own section
        out[k] = v
    return out


def _fmt(value: datetime | None) -> str:
    if value is None:
        return "n/a"
    return value.isoformat()


def _fmt_value(value: Any) -> str:
    if isinstance(value, float):
        return f"{value:.6f}"
    return str(value)


__all__ = ["render_report"]
