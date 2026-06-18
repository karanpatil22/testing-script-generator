# Technical Specification Document

**Playwright Recorder — Recording-only Edition**

Version 2.0 · June 2026

---

## 1. Introduction

### 1.1 Purpose

Implementation-level reference for the **Playwright Recorder**: a local Python
server plus a browser UI that records interactions with `playwright codegen` and
optionally polishes them into clean Python tests.

### 1.2 Scope

Technology stack, project structure, module specs, the backend API contract, the
Nvidia NIM contract (polish only), prompt rules, setup, and troubleshooting.

## 2. Technology Stack

| Layer | Technology | Version | Purpose |
|---|---|---|---|
| UI | Vanilla HTML/CSS/JS (ES modules) | ES2022+ | Recording interface — no build step |
| Backend | Python `http.server` (stdlib) | 3.9+ | Serve UI; run `codegen`; no third-party deps |
| Recorder | Playwright (Python) | >=1.40 | `playwright codegen` capture engine |
| Test runner | pytest + pytest-playwright + pytest-asyncio | latest | Run generated tests |
| AI (optional) | Nvidia NIM (OpenAI-compatible) | qwen3-next-80b-a3b-instruct | Polish step only (non-reasoning code model) |
| HTTP client | Fetch API (browser) | — | `/api/record` and NIM calls |

### 2.1 Local dependencies (installed by `setup.sh`)

```
python3 -m venv .venv
.venv/bin/python -m pip install playwright pytest pytest-playwright pytest-asyncio
.venv/bin/python -m playwright install chromium
```

Requires Python 3.9+ with `venv`/`ensurepip` (Debian/Ubuntu: `sudo apt install python3-venv`).

### 2.2 Nvidia NIM (optional, polish only)

Free key from https://build.nvidia.com (prefixed `nvapi-`). Configure it
**server-side** — the `NVIDIA_API_KEY`/`NVIDIA_NIM_KEY` env var, or a
`nim_key.txt` file next to `server.py`. The key is never sent to the browser.
Without it, the app shows raw `codegen` output. Free tier ~40 requests/minute.

## 3. Project Structure

```
playwright-recorder/
├── server.py              # Static server + POST /api/record (codegen) + POST /api/polish (NIM proxy)
├── setup.sh               # Create .venv, install Playwright + Chromium
├── run.sh                 # Launch server.py from .venv
├── nim_key.txt            # Optional: Nvidia NIM key for polish (do not commit)
├── index.html             # Recording UI
├── styles/
│   └── app.css
├── scripts/
│   ├── main.js            # Recording orchestration + Raw/Polished toggle
│   ├── recorderClient.js  # Calls POST /api/record and POST /api/polish
│   ├── promptBuilder.js   # buildRecordingPrompt (polish prompt)
│   ├── responseParser.js  # Strip markdown fences
│   └── ui.js              # DOM helpers (loading text, download, copy)
├── tests/                 # Real Playwright tests (kept as reference)
├── MD/                    # PRD / SDD / TSD / README
└── README.md
```

## 4. Module Specifications

### 4.1 server.py (backend)

**`run_codegen(url, target) -> (code, error)`**

Spawns codegen and blocks until the user closes the window:

```python
cmd = [sys.executable, "-m", "playwright", "codegen",
       "--target", target, "-o", out_path, url]
proc = subprocess.run(cmd, capture_output=True, text=True)  # no shell=True
```

Returns the temp file contents, or a mapped error message
("Playwright is not installed…", "Browser not installed. Run: python -m
playwright install chromium").

**HTTP handler**

| Route | Method | Behaviour |
|---|---|---|
| `/` and static paths | GET | Serve files under project root; 404 on traversal/miss |
| `/api/record` | POST | Body `{url, target?}`; validate URL is `http(s)`; whitelist target (default `python-pytest`); run codegen; return `{code}` or `{error}` |

Binds `127.0.0.1:${PORT:-8000}`; `ThreadingHTTPServer`.

### 4.2 recorderClient.js

```js
recordWorkflow(url, target = 'python-pytest'): Promise<string>
```
POSTs to `/api/record`. No fetch timeout (held open for the whole recording).
Throws on: server unreachable, non-OK response (uses backend `error`), empty
recording.

```js
polishRecording(prompt): Promise<string>
```
POSTs to `/api/polish` (backend proxy to NIM). Returns the raw model output
(caller runs `parseCode`). Throws on server-unreachable or non-OK response.

### 4.3 promptBuilder.js

```js
buildRecordingPrompt(recording, description?): string
```
Single prompt. Instructs the model to keep recorded locators verbatim, convert
sync → async, extract magic strings to constants, drop mouse-move/hover noise,
add inferred assertions, emit one async pytest function, return ONLY code.

> The legacy `buildDescriptionPrompt` and `buildURLPrompt` were removed.

### 4.4 Polish proxy (server.py)

There is **no client-side NIM client** — the browser can't reach NIM (CORS).
`server.py` handles it:

```python
get_nim_key() -> str        # env NVIDIA_API_KEY/NVIDIA_NIM_KEY, else ./nim_key.txt
polish(prompt) -> (code, error)
```
`polish()` calls `https://integrate.api.nvidia.com/v1/chat/completions` (model
`qwen/qwen3-next-80b-a3b-instruct`, `max_tokens` 4000, `temperature` 0.2, `top_p` 0.95,
`Authorization: Bearer <key>`) via stdlib `urllib`, and maps missing-key /
401 / 429 / network errors to messages returned as `{error}`.

### 4.5 responseParser.js

```js
parseCode(rawText): string   // trim, strip ```lang fences, trim
```

### 4.6 ui.js

| Function | Description |
|---|---|
| `showOutput()` | Reveal output section + spinner |
| `showLoading()` / `setLoadingText(t)` | Spinner on; update status (recording vs. polishing) |
| `displayCode(code)` | Render code, hide spinner |
| `showError(msg)` / `hideError()` | Styled error div |
| `copyCode()` | Clipboard copy with feedback |
| `downloadCode(name)` | Download current view as `test_<slug>.py` |

### 4.7 main.js

State `{ raw, polished, view }`. Flow: validate URL → `recordWorkflow` → if
polish enabled, best-effort `polishRecording` → render. Toggle chooses
Raw/Polished; Copy/Download act on the current view. Polish errors (including
"no key configured", returned by the backend) are non-fatal — fall back to raw
+ notice.

## 5. Backend API Contract

### 5.1 POST /api/record

**Request**
```json
{ "url": "https://app.example.com/login", "target": "python-pytest" }
```
**Response (200)** — `{ "code": "<generated Python test>" }`

| Code | Cause | Body |
|---|---|---|
| 400 | URL not `http(s)` / bad JSON | `{ "error": "URL must start with http:// or https://" }` |
| 404 | Unknown endpoint | `{ "error": "Unknown endpoint" }` |
| 500 | codegen failed / Playwright missing | `{ "error": "Playwright is not installed. Run ./setup.sh first." }` |

Valid `target` values: `python-pytest` (default), `python`, `python-async`, `javascript`.

### 5.2 POST /api/polish

**Request** — `{ "prompt": "<polish prompt>" }`
**Response (200)** — `{ "code": "<raw model output>" }` (client runs `parseCode`)

| Code | Cause | Body |
|---|---|---|
| 400 | Missing prompt / bad JSON | `{ "error": "Missing prompt" }` |
| 502 | No key configured, or NIM error (401/429/network) | `{ "error": "No Nvidia NIM API key configured. Set NVIDIA_API_KEY or create a nim_key.txt file next to server.py." }` |

## 6. Nvidia NIM Contract (polish only, server-side)

Called **only** from `server.py`, never the browser. OpenAI-compatible: request
`{model, max_tokens, temperature, top_p, messages:[{role,content}]}`; response
`choices[0].message.content`. Used solely to polish a raw recording — never to
infer selectors.

## 7. Environment Setup

```bash
./setup.sh        # one time: .venv + Playwright + Chromium
./run.sh          # start server at http://127.0.0.1:8000
# open the URL, enter your app URL, click Start Recording
```

> `codegen` opens a headed browser, so run on a desktop session (not headless SSH).

### 7.1 Running a generated test

```bash
# pytest.ini
[pytest]
asyncio_mode = auto

.venv/bin/pytest test_recorded.py            # headless
.venv/bin/pytest test_recorded.py --headed   # visible
```

## 8. Prompt Engineering Guidelines (polish)

The polish prompt's first duty is **fidelity**: never alter recorded locators.
Beyond that, the same house-style rules apply — async API, `@pytest.mark.asyncio`,
no `time.sleep()`, at least one `expect()` per major action, constants block,
step comments, "return ONLY code". Keep `temperature` low (0.2) for
deterministic output.

## 9. Extension Points

- **codegen target in UI** — surface a dropdown; pass `target` through to `/api/record`.
- **Extra codegen flags** — extend `run_codegen` (e.g. `--device`, `--save-trace`).
- **JS/TS output** — set `target: "javascript"` and add a JS polish prompt.

## 10. Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| "Could not reach the local recorder server" | `server.py` not running | `./run.sh` |
| "Playwright is not installed" | venv missing deps | `./setup.sh` |
| "Browser not installed" | Chromium not downloaded | `.venv/bin/python -m playwright install chromium` |
| codegen window never opens | Headless/no display | Run on a desktop session |
| Polish step does nothing | No `nvapi-` key | Set `NVIDIA_API_KEY` env var or create `nim_key.txt`, then restart `./run.sh` (raw output still works) |
| 429 from NIM | Free-tier rate limit | Wait ~60s and retry |

## 11. Migration from v1.x (three-mode AI generator)

| Area | v1.x | v2.0 |
|---|---|---|
| Input modes | Workflow / URL / Recording-import (paste) | **Recording only** (integrated codegen) |
| Selectors | Inferred by LLM from prose | Captured from the live DOM |
| Backend | None (single HTML file) | `server.py` (required to run codegen) |
| AI role | Generate the whole test | **Polish** a real recording (optional) |
| Removed | `buildDescriptionPrompt`, `buildURLPrompt`, tab controller, paste UI | — |
| Added | `server.py`, `recorderClient.js`, `setup.sh`, `run.sh`, Raw/Polished toggle, download | — |
