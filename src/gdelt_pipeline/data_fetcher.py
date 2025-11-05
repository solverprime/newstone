"""Utilities for acquiring GDELT data."""

from __future__ import annotations

import logging
import os
from urllib.parse import urlparse

import numpy as np
import pandas as pd
from dateutil import tz

from .config import ALL_DOMAINS, ANALYSIS_WINDOW, PLACE_SPECS

LOGGER = logging.getLogger(__name__)


def _parse_tone(tone_str: str) -> float | None:
    if not tone_str:
        return None
    try:
        return float(tone_str.split(",")[0])
    except (ValueError, IndexError):
        return None


def _domain_from_url(url: str) -> str:
    parsed = urlparse(url)
    host = parsed.netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    return host


def _mock_dataset() -> pd.DataFrame:
    rng = np.random.default_rng(42)
    start, end = ANALYSIS_WINDOW
    dates = pd.date_range(start=start, end=end, freq="D")
    records = []
    for spec in PLACE_SPECS.values():
        for date in dates:
            if rng.random() < 0.35:
                continue
            domain = rng.choice(spec.domains)
            tone = np.clip(rng.normal(loc=rng.uniform(-5, 5), scale=20), -100, 100)
            url = f"https://{domain}/mock/{date.strftime('%Y%m%d')}/{rng.integers(0, 1_000_000)}"
            records.append(
                {
                    "ts_utc": date.to_pydatetime().replace(tzinfo=tz.UTC),
                    "domain": domain,
                    "url": url,
                    "tone_native": tone,
                    "place": spec.slug,
                }
            )
    df = pd.DataFrame.from_records(records)
    return df


def fetch_gdelt_data(use_mock: bool = False) -> pd.DataFrame:
    """Retrieve raw GDELT rows containing tone information."""

    if use_mock:
        LOGGER.warning("Using mock dataset for development/testing.")
        return _mock_dataset()

    source = os.getenv("GDELT_SOURCE", "bigquery").lower()
    if source == "bigquery":
        return _fetch_from_bigquery()
    raise ValueError(f"Unsupported GDELT_SOURCE: {source}")


def _fetch_from_bigquery() -> pd.DataFrame:
    try:
        from google.cloud import bigquery
    except ImportError as exc:  # pragma: no cover - import guard
        raise RuntimeError(
            "google-cloud-bigquery is required for BigQuery fetching. Install it via pip."
        ) from exc

    start, end = ANALYSIS_WINDOW
    start_date = int(start.strftime("%Y%m%d"))
    end_date = int(end.strftime("%Y%m%d"))
    domain_filters = " OR ".join(
        [f"LOWER(DocumentIdentifier) LIKE '%{domain.lower()}%'" for domain in ALL_DOMAINS]
    )
    query = f"""
        SELECT
          TIMESTAMP(DATETIME(PARSE_DATE('%Y%m%d', CAST(date AS STRING)))) AS ts_utc,
          DocumentIdentifier AS url,
          V2Tone
        FROM `gdelt-bq.gdeltv2.gkg`
        WHERE date BETWEEN {start_date} AND {end_date}
          AND ({domain_filters})
    """

    client = bigquery.Client()
    job = client.query(query)
    df = job.to_dataframe()
    df["domain"] = df["url"].map(_domain_from_url)
    df["tone_native"] = df["V2Tone"].map(_parse_tone)
    df = df.dropna(subset=["tone_native", "domain"])
    df = df.drop(columns=["V2Tone"])
    df["place"] = df["domain"].map(_domain_to_place())
    df = df.dropna(subset=["place"])
    return df


def _domain_to_place() -> dict[str, str]:
    mapping: dict[str, str] = {}
    for spec in PLACE_SPECS.values():
        for domain in spec.domains:
            mapping[domain.lower()] = spec.slug
    return mapping


def assign_place_from_domain(df: pd.DataFrame) -> pd.DataFrame:
    mapping = _domain_to_place()
    df["place"] = df["domain"].str.lower().map(mapping)
    return df.dropna(subset=["place"])


