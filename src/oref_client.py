from __future__ import annotations

import json
from typing import Any

import requests

# Headers mirrored from the amitfin/oref_alert HACS integration
# (custom_components/oref_alert/coordinator.py OREF_HEADERS).
# Oref's WAF appears to gate requests on these; removing them is known to cause
# intermittent failures in the upstream project.
OREF_HEADERS = {
    "Referer": "https://www.oref.org.il/",
    "X-Requested-With": "XMLHttpRequest",
    "Content-Type": "application/json",
}


class OrefClient:
    def __init__(self, url: str, timeout_sec: float) -> None:
        self.url = url
        self.timeout_sec = timeout_sec
        self._session = requests.Session()
        self._session.headers.update(OREF_HEADERS)
        self._last_modified: str | None = None
        self._cached_payload: dict[str, Any] | list[Any] | None = None

    def fetch(self) -> tuple[dict[str, Any] | list[Any] | None, str | None]:
        headers: dict[str, str] = {}
        if self._last_modified:
            headers["If-Modified-Since"] = self._last_modified

        try:
            response = self._session.get(
                self.url, headers=headers or None, timeout=self.timeout_sec
            )
        except requests.RequestException as exc:
            return None, f"request_error: {exc}"

        if response.status_code == 304:
            return self._cached_payload, None

        try:
            response.raise_for_status()
        except requests.RequestException as exc:
            return None, f"request_error: {exc}"

        payload, parse_error = self._parse(response)
        if parse_error:
            return None, parse_error

        self._cached_payload = payload
        last_modified = response.headers.get("Last-Modified")
        if last_modified:
            self._last_modified = last_modified
        return payload, None

    @staticmethod
    def _parse(
        response: requests.Response,
    ) -> tuple[dict[str, Any] | list[Any] | None, str | None]:
        try:
            return response.json(), None
        except (json.JSONDecodeError, ValueError):
            try:
                decoded = response.content.decode("utf-8-sig")
                return json.loads(decoded), None
            except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
                return None, f"parse_error: {exc}"
