from __future__ import annotations

import requests

from classifier import EventState
from config import WledConfig


class WledClient:
    def __init__(self, config: WledConfig, timeout_sec: float = 2.0) -> None:
        self.config = config
        self.timeout_sec = timeout_sec
        self._session = requests.Session()

    def target_url_for_state(self, state: EventState) -> str | None:
        if state == EventState.PRE_ALERT:
            return self.config.resolve_url(self.config.path_pre_alert)
        if state == EventState.ALERT:
            return self.config.resolve_url(self.config.path_alert)
        if state == EventState.END:
            return self.config.resolve_url(self.config.path_end)
        return None

    def trigger(self, state: EventState) -> tuple[bool, str]:
        url = self.target_url_for_state(state)
        if not url:
            return True, "no_trigger_for_state"
        try:
            response = self._session.get(url, timeout=self.timeout_sec)
            response.raise_for_status()
            return True, f"triggered:{url}"
        except requests.RequestException as exc:
            return False, f"trigger_failed:{url}:{exc}"
