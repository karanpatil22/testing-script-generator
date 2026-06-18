from playwright.sync_api import sync_playwright
import os

# ================= CONFIG =================
BASE_URL = "https://bp8uat.gieom.com"
USERNAME = "karan"
PASSWORD = "Password@12"
BASE_ROLE_NAME = "Automation_Test_Role"
COUNTER_FILE = "role_counter.txt"
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

        # Password (REAL FIX: use keyboard typing)
        password_field = page.locator("#pw-plain-text")
        password_field.wait_for()
        password_field.click()

        # remove readonly just in case
        password_field.evaluate("el => el.removeAttribute('readonly')")

        # 🔥 IMPORTANT: type like real user
        page.keyboard.type(PASSWORD, delay=50)

        # Click login
        page.locator("//button[contains(text(),'Login')]").click()

        # Wait for navigation
        page.wait_for_load_state("networkidle")

        # 🔍 Check if still on login page
        if "Login" in page.url:
            raise Exception("Login failed (still on login page)")

        print("✅ Logged in successfully")

        # -------- COUNTER --------
        counter = read_counter()
        print("Starting from counter:", counter)

        while True:
            new_role_name = (
                BASE_ROLE_NAME if counter == 0 else f"{BASE_ROLE_NAME}_{counter}"
            )

            print("Trying role:", new_role_name)

            page.goto(f"{BASE_URL}/FunctionalRoles/Create")

            name_field = page.locator("input[name='Name']")
            name_field.wait_for()
            name_field.fill(new_role_name)

            page.locator("#btnSave").click()

            page.wait_for_timeout(2000)

            error = page.locator("#divNameValidationErrors")

            if error.is_visible():
                print("❌ Name exists. Increasing counter...")
                counter += 1
                continue
            else:
                print("✅ TEST PASSED: Role created:", new_role_name)
                save_counter(counter + 1)
                break

        page.wait_for_timeout(5000)

    except Exception as e:
        print("❌ ERROR:", str(e))
        page.screenshot(path="error.png")
        print("📸 Screenshot saved as error.png")

    finally:
        browser.close()