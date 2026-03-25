import undetected_chromedriver as uc
import requests
from selenium.webdriver.common.by import By
from dotenv import load_dotenv
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import subprocess
import os
from datetime import datetime  # --- For timestamped screenshots ---

# --- CONFIGURATION ---
# Load the variables from the .env file
load_dotenv()

BASE_PATH = os.path.expanduser(os.getenv("BASE_PATH"))  # your hidden profiles folder
SS_PATH = os.path.expanduser(os.getenv("SS_PATH"))  # your screenshot folder
URL = os.getenv("CLAIM_URL")  # website url
TOKEN = os.getenv("BOT_FATHER_TOKEN")  # your BotFather token here
ID = os.getenv("USER_INFO_BOT_ID")  # your UserInfoBot ID here

# Automatically get all folder names inside that directory
# We skip hidden files (starting with '.') and common system files
ACCOUNTS = [
    f for f in os.listdir(BASE_PATH)
    if os.path.isdir(os.path.join(BASE_PATH, f)) and not f.startswith(".")
]

# Sort them alphabetically so the run is predictable
ACCOUNTS.sort()

# Define the notification function


def notify_user(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    try:
        requests.post(url, json={"chat_id": ID, "text": text, "parse_mode": "Markdown"})
        print(text)
    except Exception as e:
        print(f"Telegram failed: {e}")


# Force-close Chrome between accounts.
def kill_chrome_zombies():
    """Forcefully clears any hanging Chrome processes to prevent session locks."""
    try:
        # 'pkill -f' looks for any process with 'chrome' in the name and kills it
        subprocess.run(["pkill", "-f", "chrome"], stderr=subprocess.DEVNULL)
        time.sleep(2)  # Short pause to let the OS clean up memory
    except Exception:
        pass


# Define the main function
def run_farm(acc_name):
    print(f"\n🚀 Starting harvest for: {acc_name}")

    options = uc.ChromeOptions()
    options.add_argument(f"--user-data-dir={os.path.join(BASE_PATH, acc_name)}")

    # Running 'headless' makes it invisible (no windows pop up).
    options.add_argument("--headless")
    driver = None  # Initialize as None so 'finally' doesn't crash
    status = "Failed"
    emoji = "❓"  # --- Default emoji ---
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")  # timestamp for screenshot
    screenshot_path = (
        f"{SS_PATH}{acc_name}_{timestamp}.png"  # --- For screenshot path ---
    )

    try:
        # Wrap the creation of the driver specifically
        try:
            driver = uc.Chrome(options=options, version_main=143)
        except Exception as e:
            print(f"❌ Failed to initialize Chrome for {acc_name}: {e}")
            return "Driver Crash", "💀"

        driver.get(URL)

        # Give the site time to load cookies and clear the 'Sign In' flash
        time.sleep(8)

        # Check if we are logged out
        login_check = driver.find_elements(
            By.XPATH, "//*[contains(translate(text(), 'SIGN', 'sign'), 'sign in')]"
        )
        if len(login_check) > 0:
            emoji = "🔴"
            status = "Logged Out"
            notify_user(
                f"*{emoji} {acc_name}:*\nAccount has been logged out. Skipping."
            )
        else:
            # Check if already claimed for today (look for the 'Claimed for today!' message)
            claimed_today = driver.find_elements(
                By.XPATH, "//p[contains(text(), 'Claimed for today!')]"
            )
            if len(claimed_today) > 0:
                emoji = "🟡"
                status = "Already Claimed"
                notify_user(f"*{emoji} {acc_name}:*\nTokens already claimed for today.")
            else:
                try:
                    # Look for the Claim button
                    wait = WebDriverWait(driver, 15)
                    # This looks for a button that contains 'Claim' AND has the specific 'indigo-600' class
                    claim_btn = wait.until(
                        EC.element_to_be_clickable(
                            (
                                By.XPATH,
                                "//button[contains(@class, 'bg-indigo-600') and contains(., 'Claim')]",
                            )
                        )
                    )

                    claim_btn.click()
                    emoji = "🟢"
                    status = "Success"
                    notify_user(f"*{emoji} {acc_name}:*\nTokens successfully claimed!")
                    time.sleep(
                        3
                    )  # Let the site save the click (short sleep after click is OK)
                except Exception as e:
                    # --- Button not found or not clickable ---
                    emoji = "⚠️"
                    status = "Button Not Found"
                    # --- Screenshot on failure ---
                    os.makedirs("screenshots", exist_ok=True)
                    driver.save_screenshot(screenshot_path)
                    notify_user(
                        f"*{emoji} {acc_name}:*\nClaim button not found. Site may have changed. Screenshot saved: {screenshot_path}"
                    )
    except Exception as e:
        # --- Catch-all for unexpected errors ---
        emoji = "🚫"
        status = "Site Unreachable"
        # --- Screenshot on failure ---
        os.makedirs("screenshots", exist_ok=True)
        if "driver" in locals() and driver:
            driver.save_screenshot(screenshot_path)
        notify_user(
            f"*{emoji} {acc_name}:*\nSite Unreachable: {str(e)}. Screenshot saved: {screenshot_path}"
        )
    finally:
        if driver:
            driver.quit()

    return status, emoji


results = {}

start_time = time.time()  # --- Start timer ---

notify_user(
    f"*🚜 STARTING THE TOKEN FARM...*\n📂 Found _{len(ACCOUNTS)}_ accounts in the vault"
)

# --- THE MAIN LOOP ---
for acc in ACCOUNTS:
    try:
        # Kill any zombies from the previous account before starting a new one
        kill_chrome_zombies()

        result, emoji = run_farm(acc)
        results[acc] = (result, emoji)
    except Exception as e:
        # This is the 'Safety Net' that keeps the loop moving
        notify_user(f"🔥 Serious error on {acc}: {e}")
        results[acc] = ("Loop Error", "💥")

    print(f"--- 💤 Resting for 15s to stay under the radar ---")
    time.sleep(15)

# After the loop finishes, one last cleanup
kill_chrome_zombies()
end_time = time.time()  # --- End timer ---
total_seconds = int(end_time - start_time)
minutes, seconds = divmod(total_seconds, 60)

# --- THE FINAL REPORT ---

# Create the message content
report_header = f"📋 *Report Summary:*\n\n 🚜 *Harvested:* {len(ACCOUNTS)} Accounts\n⏱️ *Duration:* {minutes}m {seconds}s\n"


# --- Map statuses to report lines with matching emojis ---
def format_report(acc, status, emoji):
    text = f"{emoji} {acc}: "
    return text + (status if status else "Unknown Status")


report_body = "\n".join(
    [format_report(acc, status, emoji) for acc, (status, emoji) in results.items()]
)

full_message = report_header + "```\n" + report_body + "\n```"

# Fire it off!
notify_user(full_message)
