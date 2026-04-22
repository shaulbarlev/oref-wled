# oref-wled

Poll the Oref alerts API and listen to the Tzeva Adom WebSocket in parallel, classify event state for configured cities, and trigger WLED endpoints per state transition.

## Signal sources

Two sources are merged; whichever reports an alert first fires WLED. Same-state re-triggers within 60s are deduped.

- `oref_http`: polling of `https://www.oref.org.il/WarningMessages/alert/alerts.json`. Sends the same `Referer` / `X-Requested-With` / `Content-Type` headers as the `amitfin/oref_alert` HACS integration, plus `If-Modified-Since` conditional GETs so 304 responses skip reclassification.
- `tzevaadom`: persistent WebSocket to `wss://ws.tzevaadom.co.il/socket?platform=WEB` with `Origin: https://www.tzevaadom.co.il` and a 45s heartbeat (mirrored from the HACS integration). Typically fires 1-3s before `alerts.json` refreshes at the Oref CDN edge, which is why this project now reacts faster than a 1s poll alone.

The `amitfin/oref_alert` integration also uses a third source, Pushy MQTT (`mqtt-*.ioref.io:443`), which carries the same push channel the official Oref mobile app uses. It is not included here because it requires device registration, credential persistence, and a full MQTT client; it is tracked as a possible follow-up.

## Setup

- Create and activate a Python virtual environment.
- Install dependencies:
  - `pip install -r requirements.txt`
- Copy config template:
  - `cp config.example.yaml config.yaml`
- Edit `config.yaml` values:
  - `match.cities`: one or more city patterns (contains-match)
  - `wled.base_url` and `wled.path_*` for pre-alert/alert/end

## Run

- `python3 src/main.py --config config.yaml`

## Event classification

- `PRE_ALERT`: `cat == 10` and title `בדקות הקרובות צפויות להתקבל התרעות באזורך`
- `END`: `cat == 10` and title `האירוע הסתיים`
- `ALERT`: matched city and positive non-10 category (for example `6`, `13`, `14`)
- `IDLE`: valid payload with no match for configured cities
- `NO_DATA`: empty/invalid payload (`[]`, `{}`, parse error, or missing/empty `data`)

Only `PRE_ALERT`, `ALERT`, and `END` trigger WLED calls. `IDLE` and `NO_DATA` never trigger.

## Config keys

```yaml
oref:
  url: "https://www.oref.org.il/WarningMessages/alert/alerts.json"
  poll_interval_sec: 1
  timeout_sec: 2

match:
  cities:
    - "תל אביב - מרכז"

wled:
  base_url: "http://192.168.1.50"
  #path_pre_alert: "/win&T=2&PL=1"
  #path_alert: "/win&PL=0"
  path_end: "/win&PL=3"
  post_delay_sec: 20
  post_delay_path: "/win&PL=2"

runtime:
  dry_run: false

sources:
  tzevaadom:
    enabled: true
```

## Optional delayed fallback preset

If you set both `wled.post_delay_sec` and `wled.post_delay_path`, then after a successful `PRE_ALERT` / `ALERT` / `END` trigger:

- wait `post_delay_sec` seconds
- fire `post_delay_path` on the same `wled.base_url`

If those keys are omitted, this feature is disabled.

## Optional endpoint paths

`wled.path_pre_alert`, `wled.path_alert`, and `wled.path_end` are optional.  
If a path is missing (or empty), that state will be detected and logged, but no WLED request is sent for it.
