/**
 * ui.js
 * ----------------------------------------------------------------------------
 * DOM state helpers and output rendering. See TSD §4.4 and SDD §4.5.
 */

const $ = (id) => document.getElementById(id);

/**
 * Reveal the output section and show the loading spinner.
 * Hides any previous code block and error message.
 */
export function showOutput() {
  const section = $('output-section');
  if (section) section.hidden = false;
  hideError();
  showLoading();
}

/**
 * Show the loading spinner and hide the code block.
 */
export function showLoading() {
  const loading = $('loading');
  const wrapper = $('code-wrapper');
  if (loading) loading.hidden = false;
  if (wrapper) wrapper.hidden = true;
}

/**
 * Update the loading status text (e.g. recording vs. polishing phase).
 * @param {string} text
 */
export function setLoadingText(text) {
  const el = $('loading-text');
  if (el) el.textContent = text;
}

/**
 * Hide the loading spinner and reveal the code block.
 */
export function hideLoading() {
  const loading = $('loading');
  const wrapper = $('code-wrapper');
  if (loading) loading.hidden = true;
  if (wrapper) wrapper.hidden = false;
}

/**
 * Render cleaned code into the output <code> element.
 * @param {string} code - The cleaned Python test code.
 */
export function displayCode(code) {
  const out = $('code-output');
  if (out) out.textContent = code;
  hideLoading();
}

/**
 * Display an error message in the styled error div.
 * Also hides the spinner so the UI is not stuck loading.
 * @param {string} msg - The user-facing error message.
 */
export function showError(msg) {
  const display = $('error-display');
  const message = $('error-message');
  const loading = $('loading');
  if (message) message.textContent = msg;
  if (display) display.hidden = false;
  if (loading) loading.hidden = true;
}

/**
 * Hide the error div and clear its message.
 */
export function hideError() {
  const display = $('error-display');
  const message = $('error-message');
  if (display) display.hidden = true;
  if (message) message.textContent = '';
}

/**
 * Copy the current code output to the clipboard and give visual feedback.
 * Uses navigator.clipboard.writeText with a textarea fallback.
 * @returns {Promise<void>}
 */
export async function copyCode() {
  const out = $('code-output');
  const btn = $('copy-btn');
  const text = out ? out.textContent : '';
  if (!text) return;

  try {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      await navigator.clipboard.writeText(text);
    } else {
      // Fallback for non-secure contexts.
      const ta = document.createElement('textarea');
      ta.value = text;
      ta.style.position = 'fixed';
      ta.style.opacity = '0';
      document.body.appendChild(ta);
      ta.select();
      document.execCommand('copy');
      document.body.removeChild(ta);
    }

    if (btn) {
      const original = btn.textContent;
      btn.textContent = '✓ Copied!';
      btn.classList.add('copied');
      setTimeout(() => {
        btn.textContent = original;
        btn.classList.remove('copied');
      }, 1800);
    }
  } catch (err) {
    showError('Could not copy to clipboard. Please copy the code manually.');
  }
}

/**
 * Download the current code output as a .py file.
 * @param {string} [name] - Optional test name used to build the filename.
 */
export function downloadCode(name) {
  const out = $('code-output');
  const text = out ? out.textContent : '';
  if (!text) return;

  const slug = (name || 'recorded')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/^_+|_+$/g, '') || 'recorded';
  const filename = `test_${slug}.py`;

  const blob = new Blob([text], { type: 'text/x-python' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
