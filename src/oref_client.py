from __future__ import annotations

import json
from typing import Any

import requests


class OrefClient:
    def __init__(self, url: str, timeout_sec: float) -> None:
        self.url = url
        self.timeout_sec = timeout_sec
        self._session = requests.Session()

    def fetch(self) -> tuple[dict[str, Any] | list[Any] | None, str | None]:
        try:
            response = self._session.get(self.url, timeout=self.timeout_sec)
            response.raise_for_status()
        except requests.RequestException as exc:
            return None, f"request_error: {exc}"

        try:
            return response.json(), None
        except json.JSONDecodeError as exc:
            return None, f"parse_error: {exc}"
