"""End-to-end runner for the GDELT analysis pipeline."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from . import config
from .analysis import compare_latest_vs_decade, identify_outliers, rank_with_cis
from .data_fetcher import assign_place_from_domain, fetch_gdelt_data
from .io_utils import write_csv, write_parquet
from .metrics import compute_annual_metrics, compute_monthly_metrics, league_table_latest
from .plots import plot_annual_metric, plot_ecdf_overlay, plot_ecdf_per_place
from .report import summarize_latest_year, write_blogpost, write_findings_pdf, write_methods

LOGGER = logging.getLogger("gdelt_pipeline")


OUTPUT_DIRS = {
    "data": Path("data"),
    "fig": Path("fig"),
    "report": Path("report"),
}


ASSUMPTIONS = [
    "Domain whitelists per place approximate major outlets covering the region.",
    "GDELT GKG tone element (V2Tone) is treated as the native tone score.",
    "Titles and ML sentiment replication are deferred due to rate limits; tone_native is authoritative.",
    "BigQuery access is assumed for production runs; `USE_MOCK_DATA=1` enables synthetic runs for testing.",
]


def _configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the GDELT tone analysis pipeline.")
    parser.add_argument("--use-mock-data", action="store_true", help="Generate synthetic data instead of querying GDELT.")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    _configure_logging(args.verbose)

    LOGGER.info("Fetching raw data...")
    raw_df = fetch_gdelt_data(use_mock=args.use_mock_data)
    raw_df = assign_place_from_domain(raw_df)
    raw_path = OUTPUT_DIRS["data"] / "gdelt_raw.parquet"
    write_parquet(raw_df, raw_path)
    LOGGER.info("Raw data written to %s", raw_path)

    LOGGER.info("Running preprocessing steps...")
    from .preprocess import preprocess  # Local import to avoid cycles

    clean_df = preprocess(raw_df)
    LOGGER.info("Clean dataset size: %d rows", len(clean_df))

    monthly_metrics = compute_monthly_metrics(clean_df)
    annual_metrics = compute_annual_metrics(clean_df)
    league_df = league_table_latest(annual_metrics)

    if annual_metrics.empty:
        LOGGER.warning("No annual metrics produced; exiting early.")
        return

    write_csv(monthly_metrics, OUTPUT_DIRS["data"] / "place_metrics_monthly.csv")
    write_csv(annual_metrics, OUTPUT_DIRS["data"] / "place_metrics_annual.csv")
    write_csv(league_df, OUTPUT_DIRS["data"] / "league_table_latest.csv")

    LOGGER.info("Generating plots...")
    plot_annual_metric(annual_metrics, "mean", OUTPUT_DIRS["fig"] / "annual_mean_by_place.png", "Mean Tone")
    plot_annual_metric(annual_metrics, "SWI", OUTPUT_DIRS["fig"] / "annual_swi_by_place.png", "Spread Width Index")
    plot_annual_metric(annual_metrics, "CI", OUTPUT_DIRS["fig"] / "annual_ci_by_place.png", "Congregation Index")

    latest_year = int(annual_metrics["year"].max())
    latest_year_df = clean_df[clean_df["ts_utc"].dt.year == latest_year]
    if not latest_year_df.empty:
        plot_ecdf_overlay(
            latest_year_df,
            OUTPUT_DIRS["fig"] / "ecdf_latest_year.png",
            f"ECDF of Tone in {latest_year}",
        )
    else:
        LOGGER.warning("No data available for latest year %s; skipping overlay ECDF.", latest_year)
    plot_ecdf_per_place(clean_df, OUTPUT_DIRS["fig"])

    LOGGER.info("Creating reports...")
    qc_notes = []
    totals = clean_df.groupby("place").size()
    for slug, count in totals.items():
        label = next(spec.name for spec in config.PLACE_SPECS.values() if spec.slug == slug)
        if count < 10_000:
            qc_notes.append(f"{label}: N={count:,} (<10k) — interpret estimates cautiously.")
        else:
            qc_notes.append(f"{label}: N={count:,} (sufficient volume).")

    latest_vs_decade = compare_latest_vs_decade(annual_metrics)
    outliers = identify_outliers(annual_metrics)

    rankings = [
        rank_with_cis(annual_metrics, "SWI", ("SWI_lo", "SWI_hi")),
        rank_with_cis(annual_metrics, "CI", ("CI", "CI")),
        rank_with_cis(annual_metrics, "mean", ("mean_lo", "mean_hi")),
    ]

    ranking_notes = []
    tldr_lines = []
    for insight in rankings:
        ranking_notes.append(f"### {insight.metric} ({insight.note})")
        ranking_notes.extend([f"- {line}" for line in insight.ordered_places])
        if insight.metric == "mean":
            top = insight.ordered_places[0]
            tldr_lines.append(f"Mean tone leader: {top}.")
        elif insight.metric == "SWI":
            tldr_lines.append(f"Breadth leader (SWI): {insight.ordered_places[0]}.")
        elif insight.metric == "CI":
            tldr_lines.append(f"Congregation leader: {insight.ordered_places[0]}.")

    latest_summary = summarize_latest_year(latest_vs_decade)
    outlier_notes = [
        f"- {_place_name(row['place'])} {int(row['year'])}: mean {row['mean']:.2f} (z={row['zscore']:.2f})."
        for _, row in outliers.iterrows()
    ]

    methods_path = OUTPUT_DIRS["report"] / "methods.md"
    write_methods(ASSUMPTIONS, qc_notes, methods_path)

    blogpost_path = OUTPUT_DIRS["report"] / "blogpost.md"
    write_blogpost(tldr_lines, ranking_notes, latest_summary, outlier_notes, blogpost_path)

    findings_path = OUTPUT_DIRS["report"] / "findings.pdf"
    summary_lines = tldr_lines + [latest_summary]
    write_findings_pdf(summary_lines, findings_path)

    LOGGER.info("Pipeline completed. Outputs saved under data/, fig/, and report/ directories.")


def _place_name(slug: str) -> str:
    return next(spec.name for spec in config.PLACE_SPECS.values() if spec.slug == slug)


if __name__ == "__main__":
    main()

