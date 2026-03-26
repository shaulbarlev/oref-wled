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
        path_suffix: str | None = None
        if state == EventState.PRE_ALERT:
            path_suffix = self.config.path_pre_alert
        elif state == EventState.ALERT:
            path_suffix = self.config.path_alert
        elif state == EventState.END:
            path_suffix = self.config.path_end

        if not path_suffix:
            return None
        return self.config.resolve_url(path_suffix)

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
