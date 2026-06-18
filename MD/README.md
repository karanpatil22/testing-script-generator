# Playwright Recorder — Documentation Package

Specifications for the **recording-only** Playwright Recorder. The user records
clicks with `playwright codegen`; the app returns the script and optionally
polishes it. (Earlier versions had three AI input modes — those were removed.)

> For setup and usage, see the top-level [`../README.md`](../README.md).

## Document Guide

### `PRD.md` — Product Requirements
What to build and why: problem, personas, goals/non-goals, user stories, the
single record→polish→export flow, constraints, MoSCoW.

### `SDD.md` — Software Design
Architecture and components: the browser UI, the local `server.py` backend that
runs `codegen`, the optional Nvidia NIM polish step, data flow, error handling,
and security.

### `TSD.md` — Technical Specification
Implementation detail: project structure, module signatures, the
`POST /api/record` contract, the NIM contract (polish only), setup commands,
prompt rules, troubleshooting, and the v1→v2 migration table.

## Architecture at a glance

```
Browser UI ──POST /api/record──► server.py ──► playwright codegen (real Chromium)
     ▲                                                   │
     │                          raw recording ◄──────────┘ (user closes window)
     │
     └──(optional) Nvidia NIM polish──► clean async pytest test
```

- **Locators are real** — captured from the live DOM by `codegen`, not guessed.
- **Polish is optional** — needs an `nvapi-` key; raw output always works.
- **Backend required** — `codegen` drives a real browser, so this is not a single HTML file.

## Implementation Checklist

- [x] `server.py` — static serving + `POST /api/record` runs `codegen`
- [x] `index.html` — recording-only UI (URL, name, polish toggle, output)
- [x] `scripts/recorderClient.js` — calls `/api/record`
- [x] `scripts/promptBuilder.js` — `buildRecordingPrompt` (keeps locators verbatim)
- [x] `server.py` `POST /api/polish` — proxies the polish call to NIM (key stays server-side)
- [x] `scripts/responseParser.js` — strip fences
- [x] `scripts/ui.js` — loading text, Raw/Polished render, copy, download
- [x] `scripts/main.js` — orchestration + toggle
- [x] `setup.sh` / `run.sh` — environment + launcher
- [ ] Run `./setup.sh` then `./run.sh` and record an end-to-end flow

## Success Criteria

✅ Click *Start Recording* → real Chromium opens at the URL
✅ Close the window → captured script appears
✅ Locators come from the live page (no invented selectors)
✅ Optional polish produces async pytest house-style code, locators unchanged
✅ Raw output available with no key/network; Copy and Download work
✅ Generated test runs with `pytest`

## Notes on Format

Markdown for git-friendliness and easy section references. Original `.docx`
versions (if any) in the parent `Docs/` folder describe the older three-mode
design and are superseded by these v2.0 documents.
