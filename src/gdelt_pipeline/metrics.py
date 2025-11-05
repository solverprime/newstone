"""Metric computation helpers."""

from __future__ import annotations

import logging
import math
import os
from dataclasses import dataclass
from typing import Callable, Iterable

import numpy as np
import pandas as pd

LOGGER = logging.getLogger(__name__)


@dataclass
class SummaryStats:
    n: int
    mean: float
    median: float
    std: float
    p5: float
    p95: float
    swi: float
    center_share: float
    ci: float
    mean_ci: tuple[float, float]
    swi_ci: tuple[float, float]


BINS = np.linspace(-100, 100, 22)
DEFAULT_BOOT = int(os.getenv("N_BOOT", "1000"))


def _bootstrap_ci(data: np.ndarray, func: Callable[[np.ndarray], float], n_boot: int) -> tuple[float, float]:
    if data.size == 0:
        return (np.nan, np.nan)
    rng = np.random.default_rng(123)
    stats = []
    for _ in range(n_boot):
        sample = rng.choice(data, size=data.size, replace=True)
        stats.append(func(sample))
    return (float(np.percentile(stats, 2.5)), float(np.percentile(stats, 97.5)))


def _congregation_index(data: np.ndarray) -> float:
    if data.size == 0:
        return np.nan
    counts, _ = np.histogram(data, bins=BINS)
    total = counts.sum()
    if total == 0:
        return np.nan
    probs = counts / total
    probs = probs[probs > 0]
    if probs.size == 0:
        return np.nan
    entropy = -np.sum(probs * np.log(probs))
    return 1 - entropy / math.log(len(BINS) - 1)


def summarize_series(series: pd.Series, n_boot: int = DEFAULT_BOOT) -> SummaryStats:
    data = series.to_numpy(dtype=float)
    n = data.size
    if n == 0:
        return SummaryStats(0, *(float("nan") for _ in range(10)))

    mean = float(np.mean(data))
    median = float(np.median(data))
    std = float(np.std(data, ddof=0))
    p5 = float(np.percentile(data, 5))
    p95 = float(np.percentile(data, 95))
    swi = p95 - p5
    center_share = float(np.mean(np.abs(data) <= 10))
    ci = float(_congregation_index(data))
    mean_ci = _bootstrap_ci(data, np.mean, n_boot)
    swi_ci = _bootstrap_ci(data, lambda x: np.percentile(x, 95) - np.percentile(x, 5), n_boot)
    return SummaryStats(n, mean, median, std, p5, p95, swi, center_share, ci, mean_ci, swi_ci)


def compute_group_metrics(df: pd.DataFrame, group_cols: Iterable[str]) -> pd.DataFrame:
    records = []
    for keys, group in df.groupby(list(group_cols)):
        stats = summarize_series(group["tone_native"])
        if isinstance(keys, tuple):
            record = dict(zip(group_cols, keys))
        else:
            record = {list(group_cols)[0]: keys}
        record.update(
            {
                "N": stats.n,
                "mean": stats.mean,
                "median": stats.median,
                "sd": stats.std,
                "p5": stats.p5,
                "p95": stats.p95,
                "SWI": stats.swi,
                "center_share": stats.center_share,
                "CI": stats.ci,
                "mean_lo": stats.mean_ci[0],
                "mean_hi": stats.mean_ci[1],
                "SWI_lo": stats.swi_ci[0],
                "SWI_hi": stats.swi_ci[1],
            }
        )
        records.append(record)
    metrics_df = pd.DataFrame.from_records(records)
    return metrics_df.sort_values(list(group_cols)).reset_index(drop=True)


def compute_monthly_metrics(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["year"] = df["ts_utc"].dt.year
    df["month"] = df["ts_utc"].dt.month
    return compute_group_metrics(df, ["place", "year", "month"])


def compute_annual_metrics(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["year"] = df["ts_utc"].dt.year
    return compute_group_metrics(df, ["place", "year"])


def league_table_latest(annual_metrics: pd.DataFrame) -> pd.DataFrame:
    if annual_metrics.empty:
        return annual_metrics
    latest_year = annual_metrics["year"].max()
    latest = annual_metrics[annual_metrics["year"] == latest_year].copy()
    latest["rank_mean"] = latest["mean"].rank(ascending=False, method="min")
    latest["rank_SWI"] = latest["SWI"].rank(ascending=False, method="min")
    latest["rank_CI"] = latest["CI"].rank(ascending=False, method="min")
    latest["composite_rank"] = (
        latest[["rank_mean", "rank_SWI", "rank_CI"]].mean(axis=1)
    )
    latest = latest.sort_values("composite_rank")
    return latest.reset_index(drop=True)

