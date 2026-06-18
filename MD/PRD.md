# Product Requirements Document

**Playwright Recorder**

Record clicks with Playwright `codegen` and produce a polished, ready-to-run Python test.

| | |
|---|---|
| **Version** | 2.0 — Recording-only Edition |
| **Date** | June 2026 |
| **Status** | Approved for Development |
| **Platform** | Local web app (Python backend + browser UI) |

---

## 1. Executive Summary

Writing UI tests by hand is slow and requires knowing both Playwright's API and
the application under test. Playwright already ships an excellent recorder
(`codegen`) that captures **stable locators from the real page** — but its raw
output still needs cleanup before it is a maintainable test.

The **Playwright Recorder** is a recording-only tool. The user enters a URL and
clicks *Start Recording*; a real Chromium window opens via `playwright codegen`;
the user navigates their app; on closing the window the captured script is
returned and (optionally) polished by an LLM into the project's house style.

> **Core value:** Click through your app, get a clean Playwright test. Locators
> come from the live DOM — not from a guess.

This is a deliberate narrowing from the previous version, which offered three
input modes (Workflow Description, URL Analysis, Recording Import). Those modes
inferred selectors from natural language and were removed. **Only real recording
remains.**

## 2. Problem Statement

| Pain Point | Who | Frequency |
|---|---|---|
| Hand-writing Playwright tests requires API knowledge most testers lack | Manual testers, junior devs | Every new test |
| LLM-guessed selectors don't match the real page and fail at runtime | Everyone using description/URL generation | Every generated test |
| Raw `codegen` output is unstructured (no constants, assertions, or naming) | All Playwright users | Every recording session |

**Root cause:** The only reliable source of selectors is the live page. Anything
that infers selectors from prose produces brittle tests. The remaining real work
is turning an accurate recording into a clean test.

## 3. Goals & Non-Goals

### 3.1 Goals

| Goal | Description | Success Metric |
|---|---|---|
| G1 — Accuracy | Locators come from the real DOM via `codegen` | 0 invented selectors in output |
| G2 — Speed | Record → script in one sitting | < 2 min from click to copyable test |
| G3 — Quality | Optional polish adds constants, waits, assertions, async house style | Polished output runs under pytest |
| G4 — Resilience | Raw recording always available even with no API key / no network | Raw output shown when polish unavailable |
| G5 — Low setup | One `setup.sh`, one `run.sh` | Works after two commands |

### 3.2 Non-Goals

- Natural-language "describe a workflow" generation (removed).
- "URL + scenario" inference of selectors (removed).
- Pasting raw `codegen` text by hand (replaced by integrated recording).
- In-browser test execution.
- User accounts, saved libraries, team collaboration.
- JavaScript/TypeScript output (Python only; `codegen` target switch is a future option).

## 4. Target Users

| Persona | Detail | Why this tool |
|---|---|---|
| Manual tester → automation (primary) | Knows the app, beginner Python | Clicks through the app, gets a runnable test |
| QA engineer | Maintains suites | Faster than hand-writing; accurate locators |
| Developer | Adds regression tests for a feature | Records the feature flow in the same sitting |

## 5. User Stories & Acceptance Criteria

**US-01 (P0): Record a workflow against my app**
- User enters a URL (must start with `http://`/`https://`) and clicks *Start Recording*.
- A real Chromium window opens at that URL via `playwright codegen`.
- The user interacts; closing the window ends the session.
- The captured Python (`--target python-pytest`) is returned and displayed.
- If no interactions were recorded, a clear message is shown.

**US-02 (P0): Polish the recording (optional)**
- A "Polish with AI" checkbox is on by default.
- When enabled and an API key is configured, the raw recording is sent to Nvidia NIM with instructions to **keep captured locators verbatim** and restructure to async pytest house style.
- A **Raw ⇄ Polished** toggle lets the user compare/choose.
- If polishing fails or no key is configured, the raw recording is shown with a non-blocking notice.

**US-03 (P0): Get the script out**
- One-click **Copy** to clipboard.
- One-click **Download** as `test_<name>.py`.

**US-04 (P1): Helpful errors**
- Backend unreachable → "Could not reach the local recorder server…".
- Playwright/browser not installed → actionable message pointing at `./setup.sh` / `playwright install`.
- Errors are visible in the UI and never break it.

## 6. Key User Flow

| Step | User action | System response |
|---|---|---|
| 1 | Run `./setup.sh` once, then `./run.sh` | Server starts at `http://127.0.0.1:8000` |
| 2 | Open the URL, enter app URL, click *Start Recording* | Backend launches `playwright codegen`; Chromium opens |
| 3 | Click through the app | Playwright captures stable locators |
| 4 | Close the Chromium window | Raw script returned; polish runs if enabled |
| 5 | Toggle Raw/Polished, click Copy or Download | Script saved/copied |
| 6 | `pytest test_<name>.py` | Test runs against the app |

## 7. Constraints & Assumptions

| Constraint | Detail |
|---|---|
| Local backend required | `codegen` needs a real browser process; the app ships a small Python server (`server.py`) that runs it. Not a pure single-file app. |
| Headed browser | `codegen` opens a visible browser; requires a desktop session (not headless SSH). |
| Python toolchain | Python 3.9+ with `venv`/`ensurepip`; `setup.sh` installs Playwright + Chromium. |
| Polish is optional | Needs a Nvidia NIM key configured server-side (`NVIDIA_API_KEY` env var or `nim_key.txt`). Without it, raw `codegen` output is the deliverable. |
| Output language | Python only in v2. |

**Assumptions:** users run generated tests locally with `pytest`; the recorded
app is reachable from the user's machine.

## 8. MoSCoW

**Must:** integrated `codegen` recording; raw output always available; copy + download; URL validation; helpful errors; local server.
**Should:** AI polish with Raw/Polished toggle; configurable `codegen` target.
**Could:** JS/TS output; multiple recordings per session; Page Object Model output.
**Won't:** in-browser execution; accounts; description/URL selector inference (explicitly removed).

## 9. Revision History

| Version | Date | Change |
|---|---|---|
| 1.0–1.1 | June 2026 | Three-mode AI generator (Workflow / URL / Recording-import), Nvidia NIM. |
| 2.0 | June 2026 | **Recording-only.** Replaced all inference modes with integrated `playwright codegen` capture + optional polish. Added Python backend (`server.py`). |
