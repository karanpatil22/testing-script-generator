# Software Design Document

**Playwright Recorder — Recording-only Edition**

Version 2.0 · June 2026

---

## 1. Introduction

### 1.1 Purpose

This SDD describes the architecture and component design of the **Playwright
Recorder** — a local tool that records browser interactions with Playwright's
`codegen` and turns them into clean Python tests.

### 1.2 Scope

One input mode: **live recording**. The user supplies a URL; the backend runs
`playwright codegen`; the resulting script is returned and optionally polished by
an LLM. The previous Workflow-Description, URL-Analysis, and Recording-Import
(paste) modes have been removed.

### 1.3 Definitions

| Term | Definition |
|---|---|
| Playwright | Microsoft's cross-browser end-to-end testing framework |
| codegen | Playwright's built-in session recorder (`playwright codegen`) that emits test code from real interactions |
| Nvidia NIM | Nvidia Inference Microservices — free OpenAI-compatible LLM API used for the optional polish step |
| Polish | The optional LLM pass that restructures a raw recording into house style without changing locators |

### 1.4 References

- Playwright — https://playwright.dev
- Playwright codegen — https://playwright.dev/python/docs/codegen
- Nvidia NIM — https://build.nvidia.com/models
- pytest — https://docs.pytest.org

## 2. System Overview

### 2.1 Product Description

A local web app: a small Python server serves a browser UI and exposes one API
endpoint that launches `playwright codegen`. Because `codegen` captures locators
from the **live DOM**, selectors are accurate by construction. The optional
polish step only reshapes the recording.

### 2.2 Key Features

1. Integrated recording via `playwright codegen` (no manual paste).
2. Accurate locators from the real page (roles, labels, text, test-ids).
3. Optional LLM polish to async pytest house style — locators preserved verbatim.
4. Raw ⇄ Polished toggle; the raw recording is always available.
5. Copy and Download (`test_<name>.py`).
6. Runs locally with two commands (`setup.sh`, `run.sh`).

## 3. Architecture Design

### 3.1 High-Level Architecture

A thin browser client backed by a local Python server. The server is required
because `codegen` drives a real browser process — this cannot happen inside a
sandboxed web page. The optional polish call is also proxied through the server
(the browser cannot call Nvidia NIM directly because of CORS).

**Layers:**

- **Presentation** — HTML/CSS/JS recording UI (URL input, record button, output with toggle/copy/download).
- **Application (browser)** — orchestrates recording → polish → render.
- **Backend (local)** — `server.py`: serves static files, runs `codegen`, and proxies the polish call to NIM.
- **AI (optional)** — Nvidia NIM `/v1/chat/completions`, reached **only** via the backend.

### 3.2 Component Diagram

| Component | Type | Responsibility |
|---|---|---|
| `server.py` | Backend | Serve static UI; `POST /api/record` runs `playwright codegen`; `POST /api/polish` proxies to NIM |
| RecordPanel | UI | Collect URL, test name, polish toggle; Start Recording button |
| recorderClient | Service (browser) | `POST /api/record` (long-lived; resolves when the window closes) and `POST /api/polish` |
| PromptBuilder | Logic | Build the polish prompt (`buildRecordingPrompt`) |
| ResponseParser | Logic | Strip markdown fences from LLM output |
| OutputPanel | UI | Render Raw/Polished code; copy + download |

### 3.3 Data Flow

1. User enters URL + optional test name, clicks *Start Recording*.
2. `recorderClient` sends `POST /api/record {url, target}`.
3. `server.py` runs `python -m playwright codegen --target python-pytest -o <tmp> <url>` and **blocks** until the user closes the browser.
4. Server reads the temp file and returns `{code}`.
5. If polish is enabled: `PromptBuilder` builds the prompt → `recorderClient` `POST /api/polish` → `server.py` calls NIM → `ResponseParser` cleans the result. (If no key is configured, the backend returns an error and the UI falls back to raw.)
6. `OutputPanel` renders Polished (default) with a toggle to Raw.

## 4. Component Design

### 4.1 server.py (backend)

- Python standard library only (no third-party deps for the server itself).
- `GET /*` serves static files under the project root, with path-traversal protection.
- `POST /api/record`:
  - Validates the URL starts with `http://`/`https://`.
  - Whitelists the `codegen` target (defaults to `python-pytest`).
  - Spawns `codegen` via `subprocess.run` with **list args** (no `shell=True`).
  - Maps common failures (Playwright missing, browser not installed) to actionable messages.
- Binds to `127.0.0.1` only. `ThreadingHTTPServer` so the UI stays responsive while a recording is in progress.

### 4.2 recorderClient.js

`recordWorkflow(url, target)` — POSTs to `/api/record` and resolves with the raw
code. The fetch deliberately has no timeout: the request is open for the entire
recording session and resolves when the user closes the browser. Distinguishes
server-unreachable, server error (carrying the backend message), and
empty-recording cases.

### 4.3 promptBuilder.js

`buildRecordingPrompt(recording, description)` — one prompt. It instructs the
model to **keep the captured locators verbatim**, convert sync calls to async,
extract magic strings into constants, drop redundant mouse-move/hover events,
add inferred assertions, and emit a single async pytest function. The earlier
`buildDescriptionPrompt` and `buildURLPrompt` functions were removed.

### 4.4 Polish proxy (server-side)

The browser **cannot** call Nvidia NIM directly — the endpoint sends no
`Access-Control-Allow-Origin`, so a cross-origin request from the local UI is
blocked. The polish call is therefore proxied through the backend:

- `recorderClient.polishRecording(prompt)` → `POST /api/polish`.
- `server.py` reads the key (env `NVIDIA_API_KEY`/`NVIDIA_NIM_KEY`, or a
  `nim_key.txt` file), calls NIM (`/v1/chat/completions`, model
  `qwen/qwen3-next-80b-a3b-instruct`) via stdlib `urllib`, and returns `{code}`.

> **Model choice:** a non-reasoning code/instruct model is used deliberately.
> The original `minimaxai/minimax-m2.7` is a chain-of-thought reasoner that
> spent the entire token budget on hidden reasoning and returned empty `content`
> (or timed out) for real recordings. `qwen3-next-80b-a3b-instruct` returns code
> directly and fast.

The API key never reaches the browser. There is no client-side NIM client.

### 4.5 main.js (orchestration)

Holds `{ raw, polished, view }`. On record: shows recording status, calls
`recordWorkflow`, then (if enabled and keyed) polishes best-effort. Renders the
Raw/Polished toggle, Copy, and Download. Polish failure is non-fatal — it falls
back to raw and surfaces a notice.

### 4.6 ui.js

DOM helpers: `showOutput`, `showLoading`, `setLoadingText` (record vs. polish
phase), `displayCode`, `showError`/`hideError`, `copyCode`, `downloadCode`.

## 5. UI Design

### 5.1 Layout

Single panel (no tabs): URL field, optional test name, "Polish with AI"
checkbox, *Start Recording* button, and a "How it works" help box. Below: an
output section with a spinner (recording/polishing status) and a code block with
a Raw/Polished toggle, Copy, and Download.

### 5.2 Accessibility

Icon-only buttons carry `aria-label`; decorative icons use `aria-hidden`; inputs
have `<label>`s; the view toggle uses `role="tab"`/`aria-selected`; focus rings
are visible.

### 5.3 Responsive

100% width inputs and code block with padding; layout collapses cleanly on
narrow viewports.

## 6. Error Handling

| Source | Behaviour |
|---|---|
| URL validation | Client rejects non-`http(s)` before calling the backend |
| Backend unreachable | "Could not reach the local recorder server…" |
| `codegen` failure | Backend returns a mapped, actionable message (e.g. run `./setup.sh`, or `playwright install chromium`) |
| Empty recording | "No interactions were recorded…" |
| Polish failure | Non-fatal notice; raw recording shown |
| LLM markdown fences | `responseParser` strips them defensively |

## 7. Security Considerations

- **Localhost only.** The server binds `127.0.0.1`.
- **No shell injection.** `codegen` is spawned with list args, never `shell=True`; the URL is validated and the target is whitelisted.
- **Path traversal.** Static file serving resolves paths under the project root and rejects escapes.
- **No code execution.** Recorded/generated code is shown as text and downloaded; it is never executed by the app.
- **API key.** The polish key is read server-side only (`NVIDIA_API_KEY` env var or `nim_key.txt`) and never sent to the browser; do not commit a real key. (The legacy hardcoded client key was removed.)

## 8. Future Enhancements

| Feature | Priority | Description |
|---|---|---|
| Target selector in UI | Medium | Choose `python-pytest` / `python-async` / `javascript` for `codegen` |
| Multiple recordings | Medium | Append several recorded flows into one suite |
| Page Object Model | Low | Optional POM structuring during polish |
| Headless/trace options | Low | Pass extra `codegen` flags through the backend |
