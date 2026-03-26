from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any

PRE_ALERT_TITLE = "בדקות הקרובות צפויות להתקבל התרעות באזורך"
END_TITLE = "האירוע הסתיים"


class EventState(str, Enum):
    PRE_ALERT = "PRE_ALERT"
    ALERT = "ALERT"
    END = "END"
    IDLE = "IDLE"
    NO_DATA = "NO_DATA"


@dataclass(frozen=True)
class ClassificationResult:
    state: EventState
    reason: str
    matched_cities: list[str]
    cat: int | None
    title: str


def _to_text(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    return ""


def _parse_positive_int(value: Any) -> int | None:
    text = _to_text(value)
    if not text.isdigit():
        return None
    parsed = int(text)
    return parsed if parsed > 0 else None


def _normalize_city_list(raw_data: Any) -> list[str] | None:
    if not isinstance(raw_data, list):
        return None
    cities = [_to_text(item) for item in raw_data if isinstance(item, str) and _to_text(item)]
    return cities


def _find_matches(configured_cities: list[str], payload_cities: list[str]) -> list[str]:
    lower_payload = [city.lower() for city in payload_cities]
    matches: list[str] = []
    for configured in configured_cities:
        needle = configured.strip().lower()
        if not needle:
            continue
        if any(needle in city for city in lower_payload):
            matches.append(configured)
    return matches


def classify_event(payload: dict[str, Any] | list[Any] | None, configured_cities: list[str]) -> ClassificationResult:
    if payload is None:
        return ClassificationResult(EventState.NO_DATA, "payload_none", [], None, "")

    if isinstance(payload, list):
        if not payload:
            return ClassificationResult(EventState.NO_DATA, "payload_empty_list", [], None, "")
        return ClassificationResult(EventState.NO_DATA, "payload_unexpected_list", [], None, "")

    if not isinstance(payload, dict) or not payload:
        return ClassificationResult(EventState.NO_DATA, "payload_empty_or_invalid_object", [], None, "")

    payload_cities = _normalize_city_list(payload.get("data"))
    if payload_cities is None or not payload_cities:
        return ClassificationResult(EventState.NO_DATA, "missing_or_empty_data", [], None, _to_text(payload.get("title")))

    matches = _find_matches(configured_cities, payload_cities)
    if not matches:
        return ClassificationResult(
            EventState.IDLE,
            "no_matching_city",
            [],
            _parse_positive_int(payload.get("cat")),
            _to_text(payload.get("title")),
        )

    cat = _parse_positive_int(payload.get("cat"))
    title = _to_text(payload.get("title"))

    if cat == 10 and title == PRE_ALERT_TITLE:
        return ClassificationResult(EventState.PRE_ALERT, "category_10_pre_alert_title", matches, cat, title)

    if cat == 10 and title == END_TITLE:
        return ClassificationResult(EventState.END, "category_10_end_title", matches, cat, title)

    if cat is not None and cat > 0 and cat != 10:
        return ClassificationResult(EventState.ALERT, "positive_non_10_category", matches, cat, title)

    return ClassificationResult(EventState.IDLE, "unhandled_category_or_title", matches, cat, title)
