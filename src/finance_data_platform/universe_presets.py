"""Helpers for config-driven universe presets."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

DEFAULT_PRESET_DIR = Path("config/universes")


@dataclass(frozen=True, slots=True)
class UniversePreset:
    """Resolved universe preset metadata and ticker list."""

    name: str
    benchmark: str
    tickers: list[str]
    payload: dict[str, Any]


class UniversePresetError(ValueError):
    """Raised when a universe preset is incomplete or missing."""

def _active_preset_name(universe_payload: dict[str, Any]) -> str:
    override = os.getenv("UNIVERSE_PRESET", "").strip()
    if override:
        return override
    return str(universe_payload.get("preset", "default")).strip()


def load_universe_preset(
    preset_name: str,
    *,
    preset_dir: str | Path = DEFAULT_PRESET_DIR,
) -> UniversePreset:
    preset_path = Path(preset_dir) / f"{preset_name}.yaml"
    if not preset_path.exists():
        raise UniversePresetError(f"Universe preset not found: {preset_path}")

    payload = yaml.safe_load(preset_path.read_text(encoding="utf-8")) or {}
    benchmark = str(payload.get("benchmark", "SPY")).upper()

    tickers: list[str] = []
    for bucket in payload.get("buckets", []):
        for item in bucket.get("tickers", []):
            symbol = str(item.get("symbol", "")).upper().strip()
            if symbol:
                tickers.append(symbol)

    if not tickers:
        raise UniversePresetError(f"Universe preset has no tickers: {preset_path}")

    return UniversePreset(
        name=str(payload.get("name", preset_name)),
        benchmark=benchmark,
        tickers=list(dict.fromkeys(tickers)),
        payload=payload,
    )


def resolve_universe_payload(
    universe_payload: dict[str, Any],
    *,
    preset_dir: str | Path = DEFAULT_PRESET_DIR,
) -> dict[str, Any]:
    preset_name = _active_preset_name(universe_payload)
    if not preset_name or preset_name == "default":
        return {
            "preset": "default",
            "tickers": [str(t).upper() for t in universe_payload.get("tickers", [])],
            "benchmark": str(universe_payload.get("benchmark", "SPY")).upper(),
            "start_date": str(universe_payload.get("start_date", "2020-01-01")),
            "end_date": (
                None
                if universe_payload.get("end_date") is None
                else str(universe_payload.get("end_date"))
            ),
        }

    preset = load_universe_preset(preset_name, preset_dir=preset_dir)
    benchmark = str(universe_payload.get("benchmark") or preset.benchmark).upper()
    return {
        "preset": preset.name,
        "tickers": preset.tickers,
        "benchmark": benchmark,
        "start_date": str(universe_payload.get("start_date", "2020-01-01")),
        "end_date": (
            None
            if universe_payload.get("end_date") is None
            else str(universe_payload.get("end_date"))
        ),
    }


__all__ = [
    "DEFAULT_PRESET_DIR",
    "UniversePreset",
    "UniversePresetError",
    "load_universe_preset",
    "resolve_universe_payload",
]
