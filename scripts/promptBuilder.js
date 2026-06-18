/**
 * promptBuilder.js
 * ----------------------------------------------------------------------------
 * Builds the prompt that polishes a raw `playwright codegen` recording into a
 * clean, production-ready Python test via the Nvidia NIM polish step.
 *
 * House style enforced by the prompt:
 *   - Python async Playwright API with pytest-playwright
 *   - from playwright.async_api import Page, expect
 *   - @pytest.mark.asyncio decorator
 *   - async def test_xxx(page: Page)
 *   - Explicit smart waits (wait_for_selector / wait_for_load_state),
 *     never time.sleep()
 *   - At least one expect() assertion per major action
 *   - Docstring + "# Step N:" comments
 *   - Return ONLY code — no markdown fences, no explanations
 */

const SHARED_REQUIREMENTS = `Requirements:
1. Use Playwright's async Python API with pytest-playwright
2. Import exactly: from playwright.async_api import Page, expect
3. Decorate the test with @pytest.mark.asyncio
4. Define the test as: async def test_<name>(page: Page):
5. Add explicit waits (wait_for_selector, wait_for_load_state) — NEVER use time.sleep()
6. Assert at least one outcome per major action using expect(...)
7. Add a one-line docstring and a "# Step N:" comment before each major action
8. Extract reused values (BASE_URL, selectors) into named constants at the top
9. Return ONLY code — no explanations, markdown fences, or preamble`;

/**
 * Build a prompt that refactors a raw Playwright codegen recording.
 * @param {string} recording - Raw Playwright codegen output to refactor.
 * @param {string} [description] - Optional human-readable test name.
 * @returns {string} The prompt string.
 */
export function buildRecordingPrompt(recording, description) {
  const name =
    description && description.trim().length > 0
      ? description.trim()
      : 'recorded workflow';

  return `Refactor the following raw Playwright codegen recording into a clean,
production-ready Python test. The locators were captured from a REAL page, so
preserve them exactly — do not invent or change selectors.

Suggested test name: ${name}

Raw recording:
${recording.trim()}

Refactoring instructions:
- Convert the recorded sync code to Python async (await every Playwright call)
- Keep the recorded locators verbatim; only restructure around them
- Extract magic strings (URLs, credentials) into named constants at the top
- Remove redundant mouse-move and hover events captured by codegen
- Add assertions inferred from the recorded navigation flow
- Restructure into a SINGLE pytest-compatible async test function

${SHARED_REQUIREMENTS}`;
}
