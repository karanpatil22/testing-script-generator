# Playwright Recorder

Record your clicks with Playwright's `codegen`, then get a polished, ready-to-run
Python test. **Recording mode only** — no manual workflow descriptions.

## How it works

```
You click "Start Recording"
        │
        ▼
server.py  ──►  python -m playwright codegen <url>   (real Chromium opens)
        │            │
        │            └─ you navigate your app; Playwright captures stable locators
        │
        ▼  (you close the browser window)
Raw codegen Python  ──►  (optional) Nvidia NIM polish  ──►  shown in the UI
                                                            with Raw ⇄ Polished toggle
```

The recorder uses Playwright `codegen` as the capture engine, so locators come
from the **real page** (roles, labels, text, test-ids) — not guesses. The AI
"polish" step only restructures the recording (async pytest house style,
constants, assertions); it is told to keep the captured locators verbatim.

## Setup (one time)

```bash
./setup.sh      # creates .venv, installs Playwright + pytest, downloads Chromium
```

> Needs Python 3.9+ with `venv`/`ensurepip` (on Debian/Ubuntu:
> `sudo apt install python3-venv`).

## Run

```bash
./run.sh        # starts the local server at http://127.0.0.1:8000
```

Open <http://127.0.0.1:8000>, enter your app's URL, and click **Start Recording**.
A Chromium window opens — interact with your app, then **close the window** to
finish. The script appears below; use **Copy** or **Download** to save it.

## Optional: AI polishing

The raw codegen output works on its own. The "Polish with AI" step runs
**server-side** (`server.py` proxies the request to Nvidia NIM, so the key
never reaches the browser and there's no CORS problem). Configure a key one of
two ways:

```bash
# Option A: environment variable
NVIDIA_API_KEY=nvapi-xxxxx ./run.sh

# Option B: a key file next to server.py (already used if present)
echo "nvapi-xxxxx" > nim_key.txt
```

Get a free key (prefixed `nvapi-`) at <[https://build.nvidia.com](https://build.nvidia.com/models)>. Without a key,
the app just shows the raw codegen script.

## Files

| File | Role |
|------|------|
| `server.py` | Static file server + `POST /api/record` that runs codegen |
| `index.html` | Recording UI |
| `scripts/recorderClient.js` | Calls `/api/record` |
| `scripts/main.js` | Recording orchestration + Raw/Polished toggle |
| `scripts/promptBuilder.js` | Builds the polish prompt (keeps locators verbatim) |
| `scripts/nimApiClient.js` | Nvidia NIM client (polish step) |
| `setup.sh` / `run.sh` | Environment setup and launcher |

## Running the generated test

```bash
.venv/bin/pytest test_recorded.py
```
