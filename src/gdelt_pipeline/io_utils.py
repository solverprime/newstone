"""Helper functions for filesystem interactions."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def ensure_dir(path: str | Path) -> Path:
    path_obj = Path(path)
    path_obj.mkdir(parents=True, exist_ok=True)
    return path_obj


def write_parquet(df: pd.DataFrame, path: str | Path) -> None:
    path_obj = Path(path)
    ensure_dir(path_obj.parent)
    df.to_parquet(path_obj)


def write_csv(df: pd.DataFrame, path: str | Path) -> None:
    path_obj = Path(path)
    ensure_dir(path_obj.parent)
    df.to_csv(path_obj, index=False)


def write_text(path: str | Path, content: str) -> None:
    path_obj = Path(path)
    ensure_dir(path_obj.parent)
    path_obj.write_text(content)


def path_for(base: str, filename: str) -> Path:
    return ensure_dir(base) / filename

