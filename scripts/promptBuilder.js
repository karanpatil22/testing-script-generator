/**
 * promptBuilder.js
 * ----------------------------------------------------------------------------
 * Builds the prompt that polishes a raw `playwright codegen` recording into a
 * clean, production-ready standalone Python script via the Nvidia NIM polish step.
 *
 * House style enforced by the prompt:
 *   - Sync Playwright API (sync_playwright), NOT async/pytest
 *   - CONFIG block at the top for all magic values
 *   - with sync_playwright() as p: entry point
 *   - try / except / finally with page.screenshot() on error
 *   - page.keyboard.type(value, delay=N) for all input fields
 *   - locator.wait_for() before every interaction
 *   - Emoji-prefixed print() statements for logging
 *   - Return ONLY code — no markdown fences, no explanations
 */

const SHARED_REQUIREMENTS = `Requirements:
1. Use Playwright's SYNC API: from playwright.sync_api import sync_playwright
2. Do NOT use pytest, async def, or @pytest.mark.asyncio
3. Add a CONFIG section at the top with ALL magic values (URLs, credentials, names, flags) as named constants
4. Entry point must be: with sync_playwright() as p:
5. Use page.keyboard.type(value, delay=10) for typing into input fields — never fill() for password fields
6. Call locator.wait_for() before every click or type interaction
7. Wrap the main logic in try / except Exception as e / finally with this exact structure — the screenshot MUST be inside the except block (while the page is still alive), and browser.close() MUST only be in the finally block (never in except):

try:
    # ... main logic ...
except Exception as e:
    print("❌ ERROR:", str(e))
    try:
        page.screenshot(path="error.png")  # page is still open here
        print("📸 Screenshot saved as error.png")
    except Exception:
        pass  # ignore if page is already dead
finally:
    browser.close()  # always runs last, after screenshot
8. Use page.wait_for_load_state("networkidle") after navigation actions
9. Log every major step with an emoji-prefixed print() statement (✅ for success, ❌ for failure, 🔍 for checks)
10. If the script creates a named resource (role, user, record, etc.) that must be unique, use a counter file to avoid name collisions instead of crashing. Include these two helpers and a COUNTER_FILE constant in the CONFIG block:

def read_counter():
    if not os.path.exists(COUNTER_FILE):
        return 0
    with open(COUNTER_FILE, "r") as f:
        return int(f.read().strip())

def save_counter(value):
    with open(COUNTER_FILE, "w") as f:
        f.write(str(value))

Use them in a retry loop: start with the base name, and if the page shows a duplicate/validation error, increment the counter, update the name, and retry until creation succeeds. Save the incremented counter after success.
11. Return ONLY code — no explanations, markdown fences, or preamble`;

/**
 * Build a prompt that refactors a raw Playwright codegen recording.
 * @param {string} recording - Raw Playwright codegen output to refactor.
 * @param {string} [description] - Optional human-readable script name.
 * @returns {string} The prompt string.
 */
export function buildRecordingPrompt(recording, description) {
  const name =
    description && description.trim().length > 0
      ? description.trim()
      : 'recorded workflow';

  return `Refactor the following raw Playwright codegen recording into a clean,
production-ready standalone Python script. The locators were captured from a REAL page, so
preserve them exactly — do not invent or change selectors.

Suggested script name: ${name}

Raw recording:
${recording.trim()}

Refactoring instructions:
- Convert to sync Playwright API (sync_playwright) — remove any async/await
- Keep the recorded locators verbatim; only restructure around them
- Move all magic strings (URLs, credentials, names) into a CONFIG block at the top
- Replace fill() with page.keyboard.type(value, delay=10) for sensitive fields like passwords
- Add locator.wait_for() before every interaction
- Remove redundant mouse-move and hover events captured by codegen
- Add try / except / finally with a screenshot on error and browser.close() in finally
- Add emoji-prefixed print() logs at each major step
- If creating a uniquely-named resource, add read_counter/save_counter helpers and a while-loop that increments the name on duplicate errors

${SHARED_REQUIREMENTS}`;
}
