from __future__ import annotations

import argparse
import time

from classifier import EventState, classify_event
from config import AppConfig, load_config
from oref_client import OrefClient
from wled_client import WledClient


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Oref to WLED preset router")
    parser.add_argument("--config", required=True, help="Path to YAML config file")
    return parser.parse_args()


def _log_result(result_state: EventState, details: str) -> None:
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] state={result_state.value} {details}")


def run(config: AppConfig) -> None:
    oref = OrefClient(config.oref.url, config.oref.timeout_sec)
    wled = WledClient(config.wled, timeout_sec=config.oref.timeout_sec)
    last_state: EventState | None = None

    while True:
        payload, fetch_error = oref.fetch()
        if fetch_error:
            state = EventState.NO_DATA
            details = f"reason={fetch_error}"
            result = None
        else:
            result = classify_event(payload, config.match.cities)
            state = result.state
            details = (
                f"reason={result.reason} cat={result.cat} "
                f"title={result.title!r} matched={result.matched_cities}"
            )

        if state != last_state:
            if config.runtime.dry_run:
                _log_result(state, f"{details} action=dry_run")
            else:
                ok, msg = wled.trigger(state)
                _log_result(state, f"{details} action={msg} ok={ok}")
                if (
                    ok
                    and state in {EventState.PRE_ALERT, EventState.ALERT, EventState.END}
                    and config.wled.post_delay_sec is not None
                    and config.wled.post_delay_path
                ):
                    time.sleep(config.wled.post_delay_sec)
                    post_ok, post_msg = wled.trigger_post_delay()
                    _log_result(
                        state,
                        (
                            f"{details} action=post_delay_trigger "
                            f"delay_sec={config.wled.post_delay_sec} "
                            f"result={post_msg} ok={post_ok}"
                        ),
                    )
            last_state = state
        else:
            _log_result(state, f"{details} action=unchanged")

        time.sleep(config.oref.poll_interval_sec)


def main() -> None:
    args = _parse_args()
    config = load_config(args.config)
    run(config)


if __name__ == "__main__":
    main()
