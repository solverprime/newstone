"""Analytical helpers for interpreting computed metrics."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

import pandas as pd
import numpy as np

from .config import PLACE_SPECS


@dataclass
class RankingInsight:
    metric: str
    ordered_places: List[str]
    note: str


def _place_name(slug: str) -> str:
    return next(spec.name for spec in PLACE_SPECS.values() if spec.slug == slug)


def rank_with_cis(annual_metrics: pd.DataFrame, metric: str, ci_cols: tuple[str, str]) -> RankingInsight:
    latest_year = annual_metrics["year"].max()
    latest = annual_metrics[annual_metrics["year"] == latest_year].copy()
    descending_metrics = {"mean", "CI", "SWI"}
    latest = latest.sort_values(metric, ascending=metric not in descending_metrics, ignore_index=True)
    ordered = []
    for idx, row in latest.iterrows():
        lo = row.get(ci_cols[0], row[metric])
        hi = row.get(ci_cols[1], row[metric])
        ordered.append(
            f"{idx + 1}. {_place_name(row['place'])} ({row[metric]:.2f} [{lo:.2f}, {hi:.2f}])"
        )
    return RankingInsight(metric=metric, ordered_places=ordered, note=f"Latest year: {latest_year}")


def compare_latest_vs_decade(annual_metrics: pd.DataFrame) -> pd.DataFrame:
    latest_year = annual_metrics["year"].max()
    grouped = annual_metrics.groupby("place")
    baseline = grouped["mean"].mean().rename("ten_year_mean")
    merged = (
        annual_metrics[annual_metrics["year"] == latest_year]
        .set_index("place")
        .join(baseline)
        .reset_index()
    )
    merged["delta_mean"] = merged["mean"] - merged["ten_year_mean"]
    return merged


def identify_outliers(annual_metrics: pd.DataFrame) -> pd.DataFrame:
    grouped = annual_metrics.groupby("place")
    stats = grouped["mean"].agg(["mean", "std"]).rename(columns={"mean": "avg", "std": "sd"})
    merged = (
        annual_metrics.set_index(["place", "year"])
        .join(stats)
        .reset_index()
    )
    merged["zscore"] = np.where(
        merged["sd"].fillna(0) > 0,
        (merged["mean"] - merged["avg"]) / merged["sd"],
        0,
    )
    return merged.loc[merged["zscore"].abs() > 2]

