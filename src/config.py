from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

import yaml


@dataclass(frozen=True)
class OrefConfig:
    url: str
    poll_interval_sec: float
    timeout_sec: float


@dataclass(frozen=True)
class MatchConfig:
    cities: list[str]


@dataclass(frozen=True)
class WledConfig:
    base_url: str
    path_pre_alert: str
    path_alert: str
    path_end: str

    def resolve_url(self, path_suffix: str) -> str:
        base = self.base_url.rstrip("/") + "/"
        suffix = path_suffix.lstrip("/")
        return urljoin(base, suffix)


@dataclass(frozen=True)
class RuntimeConfig:
    dry_run: bool


@dataclass(frozen=True)
class AppConfig:
    oref: OrefConfig
    match: MatchConfig
    wled: WledConfig
    runtime: RuntimeConfig


def _require_section(payload: dict[str, Any], key: str) -> dict[str, Any]:
    section = payload.get(key)
    if not isinstance(section, dict):
        raise ValueError(f"Missing or invalid config section: {key}")
    return section


def _require_str(section: dict[str, Any], key: str) -> str:
    value = section.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Missing or invalid string for key: {key}")
    return value.strip()


def _get_number(section: dict[str, Any], key: str, default: float) -> float:
    value = section.get(key, default)
    if not isinstance(value, (int, float)) or value <= 0:
        raise ValueError(f"Missing or invalid positive number for key: {key}")
    return float(value)


def _load_cities(section: dict[str, Any]) -> list[str]:
    raw_cities = section.get("cities")
    if not isinstance(raw_cities, list):
        raise ValueError("Missing or invalid list for key: match.cities")

    cities = [city.strip() for city in raw_cities if isinstance(city, str) and city.strip()]
    if not cities:
        raise ValueError("match.cities must contain at least one non-empty string")
    return cities


def load_config(config_path: str) -> AppConfig:
    path = Path(config_path)
    if not path.exists():
        raise FileNotFoundError(f"Config file not found: {path}")

    with path.open("r", encoding="utf-8") as f:
        payload = yaml.safe_load(f)

    if not isinstance(payload, dict):
        raise ValueError("Top-level config must be a YAML object")

    oref_raw = _require_section(payload, "oref")
    match_raw = _require_section(payload, "match")
    wled_raw = _require_section(payload, "wled")
    runtime_raw = payload.get("runtime", {})
    if not isinstance(runtime_raw, dict):
        raise ValueError("runtime must be an object if provided")

    return AppConfig(
        oref=OrefConfig(
            url=_require_str(oref_raw, "url"),
            poll_interval_sec=_get_number(oref_raw, "poll_interval_sec", 1),
            timeout_sec=_get_number(oref_raw, "timeout_sec", 2),
        ),
        match=MatchConfig(cities=_load_cities(match_raw)),
        wled=WledConfig(
            base_url=_require_str(wled_raw, "base_url"),
            path_pre_alert=_require_str(wled_raw, "path_pre_alert"),
            path_alert=_require_str(wled_raw, "path_alert"),
            path_end=_require_str(wled_raw, "path_end"),
        ),
        runtime=RuntimeConfig(dry_run=bool(runtime_raw.get("dry_run", False))),
    )
