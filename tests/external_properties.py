# pyrefly: ignore [missing-import]
from playwright.sync_api import sync_playwright
import os

# ================= CONFIG =================
BASE_URL = "https://bp8uat.gieom.com"
USERNAME = "karan"
PASSWORD = "Password@12"
BASE_EP_TITLE = "Automation_Test_EP"
COUNTER_FILE = "ep_counter.txt"
HEADLESS = False
# ==========================================


def read_counter():
    if not os.path.exists(COUNTER_FILE):
        return 0
    with open(COUNTER_FILE, "r") as f:
        return int(f.read().strip())


def save_counter(value):
    with open(COUNTER_FILE, "w") as f:
        f.write(str(value))


with sync_playwright() as p:
    browser = p.chromium.launch(headless=HEADLESS)
    context = browser.new_context()
    page = context.new_page()

    try:
        # -------- LOGIN --------
        page.goto(f"{BASE_URL}/Account/Login")

        # Username
        page.locator("#UserName").wait_for()
        page.locator("#UserName").click()
        page.keyboard.type(USERNAME, delay=10)

        # Password
        password_field = page.locator("#pw-plain-text")
        password_field.wait_for()
        password_field.click()

        # Remove readonly attribute just in case
        password_field.evaluate("el => el.removeAttribute('readonly')")

        # Type like a real user
        page.keyboard.type(PASSWORD, delay=50)

        # Click login
        page.locator("//button[contains(text(),'Login')]").click()

        # Wait for navigation
        page.wait_for_load_state("networkidle")

        # Check if still on login page
        if "Login" in page.url:
            raise Exception("Login failed (still on login page)")

        print("✅ Logged in successfully")

        # -------- COUNTER --------
        counter = read_counter()
        print("Starting from counter:", counter)

        while True:
            new_ep_title = (
                BASE_EP_TITLE if counter == 0 else f"{BASE_EP_TITLE}_{counter}"
            )

            print("Trying External Property title:", new_ep_title)

            # Navigate to External Properties Create page
            page.goto(f"{BASE_URL}/ExternalProperties/Create")
            page.wait_for_load_state("networkidle")

            # Fill the Title field
            title_field = page.get_by_role("textbox", name="Title")
            title_field.wait_for()
            title_field.click()
            title_field.fill(new_ep_title)

            # Click Save
            page.get_by_role("button", name="Save").click()

            page.wait_for_timeout(2000)

            # Check for validation/duplicate errors
            # Adjust the selector below if the app uses a different error element
            error = page.locator(".validation-summary-errors, .field-validation-error, #divTitleValidationErrors")

            if error.is_visible():
                print("❌ Title already exists or validation error. Increasing counter...")
                counter += 1
                continue
            else:
                print("✅ TEST PASSED: External Property created:", new_ep_title)
                save_counter(counter + 1)
                break

        page.wait_for_timeout(5000)

    except Exception as e:
        print("❌ ERROR:", str(e))
        page.screenshot(path="ep_error.png")
        print("📸 Screenshot saved as ep_error.png")

    finally:
        browser.close()
