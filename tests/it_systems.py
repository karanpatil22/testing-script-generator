from playwright.sync_api import sync_playwright
import random
import string

# ================= CONFIG =================
BASE_URL = "https://bp8uat.gieom.com"
USERNAME = "karan"
PASSWORD = "Password@12"
IT_SYSTEM_NAME = "IT_automation_1"
HEADLESS = False
# ==========================================


def generate_random_name():
    """Generate a random 5-character alphanumeric string followed by '_IT'."""
    chars = string.ascii_lowercase + string.digits
    random_str = "".join(random.choices(chars, k=5))
    return f"{random_str}_IT"


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

        # Password (use keyboard typing to bypass readonly)
        password_field = page.locator("#pw-plain-text")
        password_field.wait_for()
        password_field.click()
        password_field.evaluate("el => el.removeAttribute('readonly')")
        page.keyboard.type(PASSWORD, delay=50)

        # Click login
        page.locator("//button[contains(text(),'Login')]").click()

        # Wait for navigation
        page.wait_for_load_state("networkidle")

        # Check if still on login page
        if "Login" in page.url:
            raise Exception("Login failed (still on login page)")

        print("✅ Logged in successfully")

        # -------- NAVIGATE TO SITE SETTINGS --------
        page.locator('a[title="settings"]').wait_for()
        page.locator('a[title="settings"]').click()
        page.wait_for_load_state("networkidle")
        print("✅ Navigated to Site Settings")

        # -------- NAVIGATE TO IT SYSTEMS --------
        page.locator("a[href='/ITSystem/List']").wait_for()
        page.locator("a[href='/ITSystem/List']").click()
        page.wait_for_load_state("networkidle")
        print("✅ Navigated to IT Systems list")

        # -------- CREATE NEW IT SYSTEM --------
        current_name = IT_SYSTEM_NAME

        while True:
            print(f"Trying name: {current_name}")

            # Navigate to Create page
            page.goto(f"{BASE_URL}/ITSystem/Create")
            page.wait_for_load_state("networkidle")

            # Fill in the Name field
            name_field = page.locator("input#Name")
            name_field.wait_for()
            name_field.fill(current_name)

            # Click Save
            page.locator("button#btnSave").click()

            page.wait_for_timeout(3000)

            # Check for duplicate name error
            error_text = page.locator("text=This name already exists")

            if error_text.is_visible():
                print(f"❌ Name '{current_name}' already exists. Generating random name...")
                current_name = generate_random_name()
                continue
            else:
                print(f"✅ IT System created successfully: {current_name}")
                break

        # Wait to see the result
        page.wait_for_timeout(3000)
        print(f"📍 Final URL: {page.url}")

    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        page.screenshot(path="error_it_system.png")
        print("📸 Screenshot saved as error_it_system.png")

    finally:
        browser.close()
