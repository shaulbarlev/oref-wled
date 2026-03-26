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
        return self.trigger_url(url)

    def trigger_post_delay(self) -> tuple[bool, str]:
        if self.config.post_delay_sec is None or not self.config.post_delay_path:
            return True, "no_post_delay_config"
        url = self.config.resolve_url(self.config.post_delay_path)
        return self.trigger_url(url)

    def trigger_url(self, url: str) -> tuple[bool, str]:
        try:
            response = self._session.get(url, timeout=self.timeout_sec)
            response.raise_for_status()
            return True, f"triggered:{url}"
        except requests.RequestException as exc:
            return False, f"trigger_failed:{url}:{exc}"
