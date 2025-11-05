"""Data cleaning utilities for the GDELT pipeline."""

from __future__ import annotations

import pandas as pd


def harmonize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["ts_utc"] = pd.to_datetime(df["ts_utc"], utc=True)
    df["domain"] = df["domain"].str.lower()
    df["tone_native"] = pd.to_numeric(df["tone_native"], errors="coerce")
    df = df.dropna(subset=["tone_native"])
    df["tone_native"] = df["tone_native"].clip(-100, 100)
    return df


def deduplicate_within_window(df: pd.DataFrame, window_hours: int = 48) -> pd.DataFrame:
    df = df.sort_values("ts_utc").copy()
    window_ns = window_hours * 3600 * 1_000_000_000
    df["bucket"] = (df["ts_utc"].view("int64") // window_ns)
    deduped = (
        df.drop_duplicates(subset=["place", "domain", "bucket", "tone_native"], keep="first")
        .drop(columns=["bucket"])
        .reset_index(drop=True)
    )
    return deduped


def mark_wire_copy(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    counts = df.groupby("url")["place"].transform("nunique")
    df["is_wire_copy"] = counts > 1
    return df


def preprocess(df: pd.DataFrame) -> pd.DataFrame:
    df = harmonize_columns(df)
    df = deduplicate_within_window(df)
    df = mark_wire_copy(df)
    return df

