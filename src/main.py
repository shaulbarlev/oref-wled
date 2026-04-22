from __future__ import annotations

import argparse
import time
from typing import Any

from classifier import EventState, classify_event
from config import AppConfig, load_config
from dispatcher import TriggerDispatcher
from oref_client import OrefClient
from tzevaadom_client import TzevaadomClient
from wled_client import WledClient


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Oref to WLED preset router")
    parser.add_argument("--config", required=True, help="Path to YAML config file")
    return parser.parse_args()


def _log_result(result_state: EventState, details: str) -> None:
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] state={result_state.value} {details}", flush=True)


def _log_info(message: str) -> None:
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}", flush=True)


def _on_tzevaadom_alert(
    dispatcher: TriggerDispatcher, source: str, info: dict[str, Any]
) -> None:
    details = (
        f"reason=tzevaadom_ws cat=? title='' "
        f"matched={info.get('matched_cities')} threat={info.get('threat')} "
        f"notification_id={info.get('notification_id')}"
    )
    dispatcher.handle(EventState.ALERT, details, source)


def run(config: AppConfig) -> None:
    oref = OrefClient(config.oref.url, config.oref.timeout_sec)
    wled = WledClient(config.wled, timeout_sec=config.oref.timeout_sec)
    dispatcher = TriggerDispatcher(
        wled=wled,
        wled_config=config.wled,
        runtime=config.runtime,
        log=_log_result,
    )

    tz_client: TzevaadomClient | None = None
    if config.sources.tzevaadom.enabled:
        tz_client = TzevaadomClient(
            cities=config.match.cities,
            on_alert=lambda source, info: _on_tzevaadom_alert(dispatcher, source, info),
            logger=_log_info,
        )
        tz_client.start()
        _log_info("tzevaadom: source enabled")
    else:
        _log_info("tzevaadom: source disabled")

    try:
        _poll_loop(config, oref, dispatcher)
    finally:
        if tz_client is not None:
            tz_client.stop()


def _poll_loop(
    config: AppConfig, oref: OrefClient, dispatcher: TriggerDispatcher
) -> None:
    last_state: EventState | None = None

    while True:
        payload, fetch_error = oref.fetch()
        if fetch_error:
            state = EventState.NO_DATA
            details = f"reason={fetch_error}"
        else:
            result = classify_event(payload, config.match.cities)
            state = result.state
            details = (
                f"reason={result.reason} cat={result.cat} "
                f"title={result.title!r} matched={result.matched_cities}"
            )

        if state != last_state:
            if state in {EventState.PRE_ALERT, EventState.ALERT, EventState.END}:
                dispatcher.handle(state, details, "oref_http")
            else:
                _log_result(state, f"{details} source=oref_http action=no_trigger_state")
            last_state = state
        else:
            _log_result(state, f"{details} source=oref_http action=unchanged")

        time.sleep(config.oref.poll_interval_sec)


def main() -> None:
    args = _parse_args()
    config = load_config(args.config)
    run(config)


if __name__ == "__main__":
    main()
