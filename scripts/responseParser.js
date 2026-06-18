/**
 * responseParser.js
 * ----------------------------------------------------------------------------
 * Cleans raw model output before display. See TSD §4.3.
 *
 * Steps (in order):
 *   1. Trim leading/trailing whitespace
 *   2. Strip an opening markdown fence (```python or ```)
 *   3. Strip a closing markdown fence (```)
 *   4. Trim again
 */

/**
 * Strip markdown code fences and surrounding whitespace from model output.
 * @param {string} rawText - The raw text returned by the API.
 * @returns {string} Cleaned, ready-to-copy code.
 */
export function parseCode(rawText) {
  if (typeof rawText !== 'string') {
    return '';
  }

  let code = rawText.trim();

  // 2. Strip opening fence: ```python, ```py, or a bare ``` on the first line.
  code = code.replace(/^```[a-zA-Z]*\r?\n?/, '');

  // 3. Strip closing fence: trailing ``` (optionally preceded by a newline).
  code = code.replace(/\r?\n?```$/, '');

  // 4. Trim again.
  return code.trim();
}
