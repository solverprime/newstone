"""FastAPI application exposing the GDELT pipeline through a web UI."""

from __future__ import annotations

import datetime as dt
import logging
from pathlib import Path
from typing import Any, Dict, Iterable, List
from urllib.parse import quote

import pandas as pd
from fastapi import BackgroundTasks, FastAPI, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from ..io_utils import ensure_dir
from ..run_all import run_pipeline

LOGGER = logging.getLogger("gdelt_pipeline.webapp")

BASE_DIR = Path(__file__).resolve().parent
TEMPLATES = Jinja2Templates(directory=str(BASE_DIR / "templates"))

# Ensure directories exist so FastAPI can mount them even on a fresh clone.
DATA_DIR = ensure_dir("data")
FIG_DIR = ensure_dir("fig")
REPORT_DIR = ensure_dir("report")

app = FastAPI(title="GDELT Tone Observatory", version="1.0")
app.mount("/data", StaticFiles(directory=str(DATA_DIR)), name="data")
app.mount("/fig", StaticFiles(directory=str(FIG_DIR)), name="fig")
app.mount("/report", StaticFiles(directory=str(REPORT_DIR)), name="report")

PIPELINE_STATE: Dict[str, Any] = {"status": "idle", "last_run": None, "error": None}


def _timestamp(path: Path) -> str:
    ts = dt.datetime.fromtimestamp(path.stat().st_mtime, tz=dt.timezone.utc)
    return ts.isoformat()


def _list_files(directory: Path, extensions: Iterable[str]) -> List[Dict[str, Any]]:
    results: List[Dict[str, Any]] = []
    if not directory.exists():
        return results
    for path in sorted(directory.glob("*")):
        if not path.suffix.lower() in extensions:
            continue
        results.append(
            {
                "name": path.name,
                "url": f"/{directory.name}/{path.name}",
                "updated": _timestamp(path),
                "size_bytes": path.stat().st_size,
            }
        )
    return results


def _load_csv_preview(path: Path, limit: int = 25) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    try:
        df = pd.read_csv(path)
    except Exception as exc:  # pragma: no cover - defensive log for unexpected formats
        LOGGER.warning("Failed to read CSV preview for %s: %s", path, exc)
        return []
    if limit:
        df = df.head(limit)
    return df.to_dict(orient="records")


def _read_text(path: Path) -> str | None:
    if not path.exists():
        return None
    try:
        return path.read_text()
    except UnicodeDecodeError:
        LOGGER.warning("Unable to decode text file at %s", path)
        return None


def _run_pipeline_background(use_mock: bool) -> None:
    PIPELINE_STATE.update({"status": "running", "error": None})
    try:
        result = run_pipeline(use_mock_data=use_mock, verbose=True)
        serializable_outputs = {
            key: str(value) if value is not None else None for key, value in result["outputs"].items()
        }
        PIPELINE_STATE.update(
            {
                "status": result.get("status", "completed"),
                "last_run": {
                    **{k: v for k, v in result.items() if k != "outputs"},
                    "outputs": serializable_outputs,
                    "completed_at": dt.datetime.now(tz=dt.timezone.utc).isoformat(),
                    "use_mock": use_mock,
                },
                "error": None,
            }
        )
    except Exception as exc:  # pragma: no cover - surfaced in UI
        LOGGER.exception("Pipeline execution failed")
        PIPELINE_STATE.update({"status": "failed", "error": str(exc)})


@app.get("/", response_class=HTMLResponse)
async def index(request: Request, message: str | None = None) -> HTMLResponse:
    annual_metrics = _load_csv_preview(DATA_DIR / "place_metrics_annual.csv")
    league_table = _load_csv_preview(DATA_DIR / "league_table_latest.csv", limit=10)
    blogpost_text = _read_text(REPORT_DIR / "blogpost.md")
    context = {
        "request": request,
        "message": message,
        "state": PIPELINE_STATE,
        "annual_metrics": annual_metrics,
        "league_table": league_table,
        "figures": _list_files(FIG_DIR, {".png", ".svg"}),
        "reports": _list_files(REPORT_DIR, {".md", ".pdf"}),
        "blogpost": blogpost_text,
    }
    return TEMPLATES.TemplateResponse("index.html", context)


@app.post("/run")
async def trigger_run(background_tasks: BackgroundTasks, use_mock_data: bool = Form(False)) -> RedirectResponse:
    background_tasks.add_task(_run_pipeline_background, use_mock_data)
    mode = "mock" if use_mock_data else "live"
    message = quote(f"Pipeline run queued using {mode} data.")
    return RedirectResponse(url=f"/?message={message}", status_code=303)


@app.get("/api/status")
async def api_status() -> Dict[str, Any]:
    return PIPELINE_STATE
