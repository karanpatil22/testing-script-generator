/**
 * recorderClient.js
 * ----------------------------------------------------------------------------
 * Talks to the local Python backend (server.py) which launches
 * `playwright codegen` and returns the generated test code.
 *
 * The request stays open for as long as the codegen browser window is open —
 * it resolves when the user closes the window.
 */

/**
 * Start a recording session via the local backend.
 * @param {string} url - The application URL to open in codegen.
 * @param {string} [target='python-pytest'] - Playwright codegen target.
 * @returns {Promise<string>} The raw generated code.
 * @throws {Error} With a user-facing message on any failure.
 */
export async function recordWorkflow(url, target = 'python-pytest') {
  let response;
  try {
    response = await fetch('/api/record', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url, target }),
    });
  } catch (networkError) {
    throw new Error(
      'Could not reach the local recorder server. Make sure server.py is running (./run.sh).'
    );
  }

  let data;
  try {
    data = await response.json();
  } catch (parseError) {
    throw new Error('Invalid response from the recorder server.');
  }

  if (!response.ok) {
    throw new Error((data && data.error) || 'Recording failed. Please try again.');
  }

  const code = (data && data.code) || '';
  if (!code.trim()) {
    throw new Error(
      'No interactions were recorded. Click through your app before closing the window.'
    );
  }
  return code;
}

/**
 * Polish a raw recording via the local backend, which proxies the request to
 * Nvidia NIM (the browser cannot call NIM directly because of CORS).
 * @param {string} prompt - The fully built polish prompt.
 * @returns {Promise<string>} The raw model output (still needs parseCode).
 * @throws {Error} With a user-facing message on any failure.
 */
export async function polishRecording(prompt) {
  let response;
  try {
    response = await fetch('/api/polish', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ prompt }),
    });
  } catch (networkError) {
    throw new Error('Could not reach the local recorder server for polishing.');
  }

  let data;
  try {
    data = await response.json();
  } catch (parseError) {
    throw new Error('Invalid response from the polish endpoint.');
  }

  if (!response.ok) {
    throw new Error((data && data.error) || 'Polishing failed.');
  }
  return (data && data.code) || '';
}
