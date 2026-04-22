from __future__ import annotations

import threading
import time
from typing import Callable

from classifier import EventState
from config import RuntimeConfig, WledConfig
from wled_client import WledClient

TRIGGER_STATES = {EventState.PRE_ALERT, EventState.ALERT, EventState.END}

LogFn = Callable[[EventState, str], None]


class TriggerDispatcher:
    """Serializes WLED triggers across HTTP and WebSocket sources.

    Two sources can report the same state within a short window (the WS push
    typically arrives seconds before alerts.json refreshes). A same-state
    trigger inside the dedup window is suppressed so the first source wins.
    """

    def __init__(
        self,
        wled: WledClient,
        wled_config: WledConfig,
        runtime: RuntimeConfig,
        log: LogFn,
        dedup_window_sec: float = 60.0,
    ) -> None:
        self._wled = wled
        self._wled_config = wled_config
        self._runtime = runtime
        self._log = log
        self._dedup_window_sec = dedup_window_sec
        self._lock = threading.Lock()
        self._last_trigger_ts: dict[EventState, float] = {}
        self._post_delay_timer: threading.Timer | None = None

    def handle(self, state: EventState, details: str, source: str) -> None:
        if state not in TRIGGER_STATES:
            self._log(state, f"{details} source={source} action=no_trigger_state")
            return

        with self._lock:
            now = time.monotonic()
            last_ts = self._last_trigger_ts.get(state)
            if last_ts is not None and (now - last_ts) < self._dedup_window_sec:
                age = now - last_ts
                self._log(
                    state,
                    f"{details} source={source} action=dedup age={age:.1f}s",
                )
                return
            self._last_trigger_ts[state] = now

        if self._runtime.dry_run:
            self._log(state, f"{details} source={source} action=dry_run")
            return

        ok, msg = self._wled.trigger(state)
        self._log(state, f"{details} source={source} action={msg} ok={ok}")

        if (
            ok
            and self._wled_config.post_delay_sec is not None
            and self._wled_config.post_delay_path
        ):
            self._schedule_post_delay(state, details, source)

    def _schedule_post_delay(self, state: EventState, details: str, source: str) -> None:
        delay = self._wled_config.post_delay_sec
        assert delay is not None

        def fire() -> None:
            post_ok, post_msg = self._wled.trigger_post_delay()
            self._log(
                state,
                (
                    f"{details} source={source} action=post_delay_trigger "
                    f"delay_sec={delay} result={post_msg} ok={post_ok}"
                ),
            )

        with self._lock:
            if self._post_delay_timer is not None:
                self._post_delay_timer.cancel()
            timer = threading.Timer(delay, fire)
            timer.daemon = True
            self._post_delay_timer = timer
            timer.start()
