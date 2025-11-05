# Headline Tone Pipeline

This repository provides an end-to-end, reproducible workflow to benchmark GDELT headline tone (`V2Tone` element 0) across Switzerland, Singapore, New York, Denver, and Hyderabad from **2015-10-16** through **2025-10-15**.

## Features

- Domain whitelists tuned to representative outlets for each place.
- BigQuery-powered extraction of GDELT GKG records (with a mock mode for offline development).
- 48-hour deduplication and wire-copy flagging.
- Monthly and annual statistics with percentile bootstrap confidence intervals for mean tone and spread width index (SWI).
- Annual trend plots plus ECDF overlays (latest year + per-place historical).
- Automated reporting: methods, PDF findings memo, and an executive-style blogpost.

## Quickstart

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

To run the entire study (defaults to synthetic data unless `--use-mock-data` is omitted and BigQuery credentials are configured):

```bash
./run_all.sh --use-mock-data
```

For production runs, ensure the `GOOGLE_APPLICATION_CREDENTIALS` environment variable is set and run:

```bash
./run_all.sh
```

Outputs are written to:

- `data/`: raw parquet plus aggregated CSV tables.
- `fig/`: annual trends and ECDF figures.
- `report/`: `methods.md`, `blogpost.md`, and `findings.pdf`.

## Interactive web experience

Spin up a FastAPI-powered control room that can execute the pipeline, monitor progress, and surface the generated artifacts.

```bash
./run_webapp.sh
# open http://localhost:8000
```

The interface provides:

- One-click pipeline runs (mock or live data) with live status polling.
- Preview tables for annual metrics and the latest league table.
- Direct links to download figures and reports as they are produced.
- Inline rendering of the auto-generated blogpost draft.

## Configuration

- Adjust domain whitelists or the analysis window in `src/gdelt_pipeline/config.py`.
- Override bootstrap iterations by setting the `N_BOOT` environment variable before running.
- Set `USE_MOCK_DATA=1` (or pass `--use-mock-data`) to avoid network calls and generate deterministic synthetic data.

## Testing

The mock-mode pipeline run serves as an integration test:

```bash
./run_all.sh --use-mock-data --verbose
```

This validates data generation, aggregation, visualization, and report creation end-to-end without external dependencies.
