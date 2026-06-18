/**
 * main.js
 * ----------------------------------------------------------------------------
 * Recording-mode app. Orchestrates:
 *   1. Launch `playwright codegen` via the local backend (recorderClient).
 *   2. Optionally polish the raw recording via the backend (POST /api/polish).
 *   3. Render raw / polished output with copy + download.
 */

import { recordWorkflow, polishRecording } from './recorderClient.js';
import { buildRecordingPrompt } from './promptBuilder.js';
import { parseCode } from './responseParser.js';
import {
  showOutput,
  showLoading,
  setLoadingText,
  displayCode,
  showError,
  hideError,
  copyCode,
  downloadCode,
} from './ui.js';

const $ = (id) => document.getElementById(id);

// Holds the two flavours of the current result so the toggle can switch views.
const state = {
  raw: '',
  polished: '',
  view: 'polished', // 'polished' | 'raw'
};

/* ── Recording orchestration ───────────────────────────────── */

function setBusy(busy) {
  const btn = $('record-btn');
  if (btn) {
    btn.disabled = busy;
    btn.textContent = busy ? '⏺ Recording…' : '⏺ Start Recording';
  }
}

async function handleRecord() {
  const url = ($('record-url-input').value || '').trim();
  const name = ($('record-name-input').value || '').trim();
  const polish = $('record-polish').checked;

  if (!/^https?:\/\//i.test(url)) {
    alert('Please enter a URL that starts with http:// or https://');
    return;
  }

  hideError();
  showOutput();
  showLoading();
  setLoadingText(
    'Recording… a Chromium window opened at your URL. Interact with your app, then close the window to finish.'
  );
  setBusy(true);

  try {
    const raw = await recordWorkflow(url, 'python-pytest');
    state.raw = raw;
    state.polished = '';

    if (polish) {
      setLoadingText('Recording captured. Polishing the script with Nvidia NIM…');
      try {
        const prompt = buildRecordingPrompt(raw, name);
        const polished = parseCode(await polishRecording(prompt));
        state.polished = polished || '';
      } catch (polishErr) {
        // Polishing is best-effort; fall back to raw and tell the user.
        showError(
          'Recording succeeded, but AI polishing failed (' +
          (polishErr.message || 'unknown error') +
          '). Showing the raw codegen output.'
        );
      }
    }

    // Default to polished if we have it, otherwise raw.
    state.view = state.polished ? 'polished' : 'raw';
    render();
  } catch (err) {
    showError(err && err.message ? err.message : 'Recording failed. Please try again.');
  } finally {
    setBusy(false);
  }
}

/* ── Rendering + view toggle ───────────────────────────────── */

function currentCode() {
  if (state.view === 'polished' && state.polished) return state.polished;
  return state.raw;
}

function render() {
  const hasPolished = Boolean(state.polished);

  // Toggle availability + active state.
  const polishedBtn = $('view-polished');
  const rawBtn = $('view-raw');
  if (polishedBtn) {
    polishedBtn.disabled = !hasPolished;
    polishedBtn.classList.toggle('active', state.view === 'polished' && hasPolished);
    polishedBtn.setAttribute('aria-selected', String(state.view === 'polished' && hasPolished));
  }
  if (rawBtn) {
    rawBtn.classList.toggle('active', state.view === 'raw' || !hasPolished);
    rawBtn.setAttribute('aria-selected', String(state.view === 'raw' || !hasPolished));
  }

  displayCode(currentCode());
}

function setView(view) {
  if (view === 'polished' && !state.polished) return;
  state.view = view;
  render();
}

/* ── Bootstrap ─────────────────────────────────────────────── */

function init() {
  const record = $('record-btn');
  if (record) record.addEventListener('click', handleRecord);

  const polishedBtn = $('view-polished');
  if (polishedBtn) polishedBtn.addEventListener('click', () => setView('polished'));

  const rawBtn = $('view-raw');
  if (rawBtn) rawBtn.addEventListener('click', () => setView('raw'));

  const copy = $('copy-btn');
  if (copy) copy.addEventListener('click', copyCode);

  const download = $('download-btn');
  if (download) {
    download.addEventListener('click', () => {
      const name = ($('record-name-input').value || '').trim();
      downloadCode(name);
    });
  }

  const dismiss = $('error-dismiss');
  if (dismiss) dismiss.addEventListener('click', hideError);
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}
