"""Plotting utilities for the GDELT pipeline."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns

from .config import PLACE_SPECS
from .io_utils import ensure_dir

sns.set_theme(style="whitegrid")


def plot_annual_metric(df: pd.DataFrame, metric: str, output_path: Path, ylabel: str) -> None:
    ensure_dir(output_path.parent)
    plt.figure(figsize=(10, 6))
    for slug, group in df.groupby("place"):
        label = next(spec.name for spec in PLACE_SPECS.values() if spec.slug == slug)
        plt.plot(group["year"], group[metric], marker="o", label=label)
        if f"{metric}_lo" in group.columns and f"{metric}_hi" in group.columns:
            plt.fill_between(
                group["year"],
                group[f"{metric}_lo"],
                group[f"{metric}_hi"],
                alpha=0.2,
            )
    plt.xlabel("Year")
    plt.ylabel(ylabel)
    plt.title(f"Annual {ylabel} by Place")
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()


def plot_ecdf_overlay(df: pd.DataFrame, output_path: Path, title: str) -> None:
    ensure_dir(output_path.parent)
    plt.figure(figsize=(10, 6))
    for slug, group in df.groupby("place"):
        label = next(spec.name for spec in PLACE_SPECS.values() if spec.slug == slug)
        if group.empty:
            continue
        sorted_vals = group["tone_native"].sort_values()
        if len(sorted_vals) == 0:
            continue
        ecdf = (sorted_vals.rank(method="first") - 1) / len(sorted_vals)
        plt.step(sorted_vals, ecdf, where="post", label=label)
    plt.xlabel("Tone")
    plt.ylabel("ECDF")
    plt.title(title)
    plt.xlim(-100, 100)
    plt.legend()
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()


def plot_ecdf_per_place(df: pd.DataFrame, output_dir: Path) -> None:
    ensure_dir(output_dir)
    for slug, group in df.groupby("place"):
        label = next(spec.name for spec in PLACE_SPECS.values() if spec.slug == slug)
        output_path = output_dir / f"ecdf_{slug}.png"
        plt.figure(figsize=(8, 5))
        if group.empty:
            continue
        sorted_vals = group["tone_native"].sort_values()
        if len(sorted_vals) == 0:
            continue
        ecdf = (sorted_vals.rank(method="first") - 1) / len(sorted_vals)
        plt.step(sorted_vals, ecdf, where="post", label=label)
        plt.xlabel("Tone")
        plt.ylabel("ECDF")
        plt.title(f"ECDF of Tone - {label}")
        plt.xlim(-100, 100)
        plt.legend()
        plt.tight_layout()
        plt.savefig(output_path)
        plt.close()

