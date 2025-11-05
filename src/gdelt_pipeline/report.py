"""Report generation helpers."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, List

import matplotlib.pyplot as plt
import pandas as pd

from .config import PLACE_SPECS
from .io_utils import ensure_dir, write_text


def write_methods(assumptions: Iterable[str], qc_notes: Iterable[str], output_path: Path) -> None:
    ensure_dir(output_path.parent)
    content = ["# Methods", "", "## Data Sources", "- GDELT GKG v2 dataset via BigQuery (tone element).", ""]
    content.append("## Assumptions")
    for assumption in assumptions:
        content.append(f"- {assumption}")
    content.append("")
    content.append("## Processing Pipeline")
    content.extend(
        [
            "1. Fetch GDELT rows filtered by whitelist domains and the study window.",
            "2. Harmonize timestamps, clip tone to [-100, 100], and deduplicate within 48 hours.",
            "3. Flag potential wire copies when identical URLs appear across multiple places.",
            "4. Aggregate monthly and annual statistics with bootstrap CIs (N_BOOT configurable).",
            "5. Render figures (annual trends, ECDFs) and assemble narrative outputs.",
        ]
    )
    content.append("")
    content.append("## Quality Checks")
    for note in qc_notes:
        content.append(f"- {note}")
    write_text(output_path, "\n".join(content))


def _place_label(slug: str) -> str:
    return next(spec.name for spec in PLACE_SPECS.values() if spec.slug == slug)


def summarize_latest_year(latest_df: pd.DataFrame) -> str:
    lines = ["Key deltas versus 10-year mean:"]
    for _, row in latest_df.iterrows():
        place = _place_label(row["place"])
        lines.append(
            f"- {place}: mean tone {row['mean']:.2f} (Δ {row['delta_mean']:+.2f} vs decade mean {row['ten_year_mean']:.2f})."
        )
    return "\n".join(lines)


def write_blogpost(
    tldr_lines: List[str],
    ranking_notes: List[str],
    latest_summary: str,
    outlier_notes: List[str],
    output_path: Path,
) -> None:
    ensure_dir(output_path.parent)
    content = ["# Headline Tone Watch: 2015-2025", "", "## TL;DR"]
    for line in tldr_lines:
        content.append(f"- {line}")
    content.append("")
    content.append("## League Table")
    content.extend(ranking_notes)
    content.append("")
    content.append("## Latest-Year vs Decade")
    content.append(latest_summary)
    content.append("")
    content.append("## Outlier Years")
    if outlier_notes:
        content.extend(outlier_notes)
    else:
        content.append("- No outlier years (|z|>2) detected.")
    content.append("")
    content.append("## ECDF Snapshot")
    content.append("- See `/fig/ecdf_latest_year.png` for a cross-market comparison of the latest distributions.")
    content.append("")
    content.append("## Closing")
    content.append("The tone mix remains fluid across markets; keep tracking the confidence intervals when comparing outlets.")
    write_text(output_path, "\n".join(content))


def write_findings_pdf(summary_lines: Iterable[str], output_path: Path) -> None:
    ensure_dir(output_path.parent)
    fig, ax = plt.subplots(figsize=(8.5, 11))
    ax.axis("off")
    text = "Findings Summary\n\n" + "\n".join(summary_lines)
    ax.text(0.05, 0.95, text, va="top", ha="left", fontsize=11, wrap=True)
    fig.savefig(output_path, format="pdf", bbox_inches="tight")
    plt.close(fig)

