"""Utility helpers for market data pipeline."""
from __future__ import annotations

import json
import os
import pathlib
import sys
from datetime import datetime, timezone
from typing import Any, Dict

import requests
from dotenv import load_dotenv

# Load environment variables from a local .env file if available.
load_dotenv()

ROOT = pathlib.Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
WEB_PUBLIC_DATA_DIR = ROOT / "web" / "public" / "data"
WEB_SRC_DATA_DIR = ROOT / "web" / "src" / "data"


class DataFetchError(RuntimeError):
    """Raised when a data request cannot be fulfilled."""


def ensure_directories() -> None:
    """Create all directories required for pipeline outputs."""
    for directory in (DATA_DIR, WEB_PUBLIC_DATA_DIR, WEB_SRC_DATA_DIR):
        directory.mkdir(parents=True, exist_ok=True)


def http_get_json(url: str, params: Dict[str, Any] | None = None) -> Dict[str, Any]:
    """Retrieve JSON data from an HTTP endpoint with basic error handling."""
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        return response.json()
    except Exception as exc:  # noqa: BLE001 - we want to surface the failure clearly
        raise DataFetchError(f"Failed to fetch data from {url}: {exc}") from exc


def write_json(data: Dict[str, Any], path: pathlib.Path) -> None:
    """Write JSON content to a file with UTF-8 encoding and sorted keys."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")


def sync_output(filename: str, payload: Dict[str, Any]) -> None:
    """Persist pipeline output to all locations consumed by the project."""
    ensure_directories()
    for directory in (DATA_DIR, WEB_PUBLIC_DATA_DIR, WEB_SRC_DATA_DIR):
        write_json(payload, directory / filename)


def today_iso() -> str:
    """Return today's date in ISO-8601 format."""
    return datetime.now(timezone.utc).date().isoformat()


def require_env(key: str) -> str:
    """Retrieve a mandatory environment variable or exit with a clear message."""
    value = os.getenv(key)
    if not value:
        print(f"Environment variable {key!r} is required but missing.", file=sys.stderr)
        raise SystemExit(1)
    return value
