# oref-wled

Poll the Oref alerts API, classify event state for configured cities, and trigger WLED endpoints per state transition.

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
```

## Optional delayed fallback preset

If you set both `wled.post_delay_sec` and `wled.post_delay_path`, then after a successful `PRE_ALERT` / `ALERT` / `END` trigger:

- wait `post_delay_sec` seconds
- fire `post_delay_path` on the same `wled.base_url`

If those keys are omitted, this feature is disabled.

## Optional endpoint paths

`wled.path_pre_alert`, `wled.path_alert`, and `wled.path_end` are optional.  
If a path is missing (or empty), that state will be detected and logged, but no WLED request is sent for it.
