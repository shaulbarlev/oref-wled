from __future__ import annotations

import json
import secrets
import threading
import time
from typing import Any, Callable

import websocket

# Values mirrored from the amitfin/oref_alert HACS integration
# (custom_components/oref_alert/tzevaadom.py). The Tzeva Adom service gates
# handshakes by Origin, so setting it is required.
WS_URL = "wss://ws.tzevaadom.co.il/socket?platform=WEB"
ORIGIN_HEADER = "https://www.tzevaadom.co.il"
WS_HEARTBEAT_SEC = 45
RECONNECT_MIN_SEC = 5.0
RECONNECT_MAX_SEC = 8.0

MESSAGE_TYPE_ALERT = "ALERT"


EventCallback = Callable[[str, dict[str, Any]], None]


class TzevaadomClient:
    def __init__(
        self,
        cities: list[str],
        on_alert: EventCallback,
        logger: Callable[[str], None] | None = None,
    ) -> None:
        self._cities_lower = [city.strip().lower() for city in cities if city.strip()]
        self._on_alert = on_alert
        self._log = logger or (lambda msg: None)
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._ws: websocket.WebSocketApp | None = None

    def start(self) -> None:
        if self._thread is not None:
            return
        self._thread = threading.Thread(
            target=self._run, name="tzevaadom-ws", daemon=True
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._ws is not None:
            try:
                self._ws.close()
            except Exception:
                pass

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                self._connect_once()
            except Exception as exc:
                self._log(f"tzevaadom: connect loop error: {exc}")
            if self._stop.is_set():
                break
            delay = secrets.SystemRandom().uniform(
                RECONNECT_MIN_SEC, RECONNECT_MAX_SEC
            )
            self._log(f"tzevaadom: reconnect in {delay:.1f}s")
            self._stop.wait(delay)

    def _connect_once(self) -> None:
        def on_open(_ws: websocket.WebSocketApp) -> None:
            self._log("tzevaadom: connected")

        def on_message(_ws: websocket.WebSocketApp, raw: str) -> None:
            self._handle_message(raw)

        def on_error(_ws: websocket.WebSocketApp, error: Any) -> None:
            self._log(f"tzevaadom: ws error: {error}")

        def on_close(
            _ws: websocket.WebSocketApp, code: Any, reason: Any
        ) -> None:
            self._log(f"tzevaadom: closed code={code} reason={reason}")

        self._ws = websocket.WebSocketApp(
            WS_URL,
            on_open=on_open,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close,
        )
        # websocket-client auto-derives Origin from the URL host, which the
        # Tzeva Adom WAF rejects (expects www.tzevaadom.co.il, not
        # ws.tzevaadom.co.il). Pass origin explicitly to override; a header=
        # entry would be sent as a second Origin line and still be rejected.
        self._ws.run_forever(
            ping_interval=WS_HEARTBEAT_SEC,
            ping_timeout=WS_HEARTBEAT_SEC - 5,
            origin=ORIGIN_HEADER,
        )

    def _handle_message(self, raw: str) -> None:
        try:
            message = json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            return
        if not isinstance(message, dict):
            return
        if message.get("type") != MESSAGE_TYPE_ALERT:
            return

        data = message.get("data")
        if not isinstance(data, dict):
            return
        if data.get("isDrill") is True:
            return

        cities = data.get("cities")
        if not isinstance(cities, list):
            return

        payload_cities = [c.strip() for c in cities if isinstance(c, str) and c.strip()]
        matches = self._match(payload_cities)
        if not matches:
            return

        details = {
            "matched_cities": matches,
            "threat": data.get("threat"),
            "notification_id": data.get("notificationId"),
            "time": data.get("time") or int(time.time()),
            "cities_count": len(payload_cities),
        }
        self._on_alert("tzevaadom", details)

    def _match(self, payload_cities: list[str]) -> list[str]:
        lower_payload = [c.lower() for c in payload_cities]
        matches: list[str] = []
        for needle in self._cities_lower:
            if any(needle in c for c in lower_payload):
                matches.append(needle)
        return matches
