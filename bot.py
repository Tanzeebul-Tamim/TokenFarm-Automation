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

# Selector values can be tweaked from the .env file if the site layout changes.
BALANCE_CONTAINER_CLASS = os.getenv("BALANCE_CONTAINER_CLASS", "bg-credit-border")
BALANCE_TEXT_CLASS = os.getenv("BALANCE_TEXT_CLASS", "text-gray-950")
CLAIM_BUTTON_CLASS = os.getenv("CLAIM_BUTTON_CLASS", "bg-indigo-600")
CLAIM_BUTTON_TEXT = os.getenv("CLAIM_BUTTON_TEXT", "Claim")
CLAIMED_STATUS_TEXT = os.getenv("CLAIMED_STATUS_TEXT", "Claimed today")
LOGIN_TEXT_FRAGMENT = os.getenv("LOGIN_TEXT_FRAGMENT", "sign in")

# Automatically get all folder names inside that directory
# We skip hidden files (starting with '.') and common system files
ACCOUNTS = [
    f
    for f in os.listdir(BASE_PATH)
    if os.path.isdir(os.path.join(BASE_PATH, f)) and not f.startswith(".")
]

# Sort them alphabetically so the run is predictable
ACCOUNTS.sort()

# Define the notification function


def notify_user(text, photo_path=None):
    try:
        if photo_path and os.path.exists(photo_path):
            # API endpoint for photos
            url = f"https://api.telegram.org/bot{TOKEN}/sendPhoto"
            with open(photo_path, "rb") as photo:
                payload = {"chat_id": ID, "caption": text, "parse_mode": "Markdown"}
                files = {"photo": photo}
                requests.post(url, data=payload, files=files)
        else:
            # Standard message endpoint
            url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
            requests.post(
                url, json={"chat_id": ID, "text": text, "parse_mode": "Markdown"}
            )
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
    status = "Failed"  # Default as 'Failed'
    balance = "Error"  # Default if 'Error'
    emoji = "❓"  # --- Default emoji ---
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")  # timestamp for screenshot
    screenshot_path = (
        f"{SS_PATH}{acc_name}_{timestamp}.png"  # --- For screenshot path ---
    )

    try:
        # Wrap the creation of the driver specifically
        try:
            driver = uc.Chrome(options=options, version_main=147)
        except Exception as e:
            # --- Handle the specific "Session Not Created" / "Connection" error ---
            error_msg = str(e)
            if (
                "session not created" in error_msg.lower()
                or "not reachable" in error_msg.lower()
            ):
                emoji, status = "🚫", "Session Crash"
            else:
                emoji, status = "❌", "Driver Error"

            notify_user(
                f"*{emoji} {acc_name}:*\n{status}. Couldn't connect to Chrome."
            )

            return status, emoji, balance

        driver.get(URL)

        # Give the site time to load cookies and clear the 'Sign In' flash
        time.sleep(8)

        # Check if we are logged out
        login_check = driver.find_elements(
            By.XPATH,
            f"//*[contains(translate(text(), 'SIGN', 'sign'), '{LOGIN_TEXT_FRAGMENT}')]",
        )

        if len(login_check) > 0:
            emoji, status = "🔴", "Logged Out"
            notify_user(
                f"*{emoji} {acc_name}:*\nAccount has been logged out. Skipping."
            )
        else:
            # Extract Balance
            # Target the span inside the credit border div
            token_xpath = (
                f"//div[contains(@class, '{BALANCE_CONTAINER_CLASS}')]//span[contains(@class, '{BALANCE_TEXT_CLASS}')]"
            )
            balance_el = driver.find_element(By.XPATH, token_xpath)
            balance = balance_el.text

            # Check if already claimed for today (look for the 'Claimed for today!' message)
            claimed_today = driver.find_elements(
                By.XPATH, f"//p[contains(text(), '{CLAIMED_STATUS_TEXT}')]"
            )
            if len(claimed_today) > 0:
                emoji, status = "🟡", "Already Claimed"
                notify_user(
                    f"*{emoji} {acc_name}:*\nTokens already claimed for today.\n\n💎 *Available Balance:* {balance}"
                )
            else:
                try:
                    # Look for the Claim button
                    wait = WebDriverWait(driver, 15)
                    # This looks for a button that contains 'Claim' AND has the specific 'indigo-600' class
                    print("starting")
                    claim_btn = wait.until(
                        EC.element_to_be_clickable(
                            (
                                By.XPATH,
                                f"//button[contains(@class, '{CLAIM_BUTTON_CLASS}') and (contains(., '{CLAIM_BUTTON_TEXT}') or contains(., 'Claim'))]",
                            )
                        )
                    )
                    print("done")

                    claim_btn.click()
                    emoji, status = "🟢", "Success"
                    balance += 200
                    notify_user(
                        f"*{emoji} {acc_name}:*\nTokens successfully claimed!\n\n💎 *New Balance:* {balance}"
                    )
                    time.sleep(
                        3
                    )  # Let the site save the click (short sleep after click is OK)
                except Exception as e:
                    # --- Button not found or not clickable ---
                    emoji, status = "⚠️", "Button Not Found"

                    # --- Screenshot on failure ---
                    os.makedirs("screenshots", exist_ok=True)
                    driver.save_screenshot(screenshot_path)

                    # Pass the screenshot_path here
                    notify_user(
                        f"{emoji} Claim button not found. Site may have changed.\nTerminating all processes!",
                        photo_path=screenshot_path,
                    )

    except Exception as e:
        # --- Catch-all for unexpected errors ---
        emoji, status = "❌", "Site Unreachable"

        # --- Screenshot on failure ---
        os.makedirs("screenshots", exist_ok=True)
        if "driver" in locals() and driver:
            driver.save_screenshot(screenshot_path)

            # Pass the screenshot_path here
            notify_user(
                f"*{emoji} {acc_name}:*\nCritical Error: {str(e)}",
                photo_path=screenshot_path,
            )
        else:
            notify_user("🚫 Site Unreachable.\nTerminating all processes!")
    finally:
        if driver:
            driver.quit()

    return status, emoji, balance


results = {}
total_farm_balance = 0  # --- Initialize total balance counter ---

start_time = time.time()  # --- Start timer ---

notify_user(f"*🚜 STARTING THE TOKEN FARM...*\n" f"*Accounts Found:* {len(ACCOUNTS)}\n")

# --- THE MAIN LOOP ---
for acc in ACCOUNTS:
    try:
        # Kill any zombies from the previous account before starting a new one
        kill_chrome_zombies()
        status, emoji, balance = run_farm(acc)

        if status == "Button Not Found" or status == "Site Unreachable":
            break

        results[acc] = (status, emoji, balance)

        if balance and balance.isdigit():
            total_farm_balance += int(balance)

    except Exception as e:
        # This is the 'Safety Net' that keeps the loop moving
        notify_user(f"💥 Loop Error\nTerminating all processes!")
        results[acc] = ("Loop Error", "💥", "N/A")

    print(f"--- 💤 Resting for 15s to stay under the radar ---")
    time.sleep(15)

# After the loop finishes, one last cleanup
kill_chrome_zombies()
end_time = time.time()  # --- End timer ---
total_seconds = int(end_time - start_time)
minutes, seconds = divmod(total_seconds, 60)

# --- THE FINAL REPORT ---

report_header = (
    "📋 *Report Summary:*\n\n"
    f"🚜 *Harvested:* {len(ACCOUNTS)} Accounts\n"
    f"💎 *Total Balance:* {total_farm_balance} Tokens\n"
    f"⏱️ *Duration:* {minutes}m {seconds}s\n"
    "📊 *Status Key:*\n"
    "       🟢 Success\n"
    "       🟡 Already Claimed\n"
    "       🔴 Logged Out\n"
    "       🚫 Session Crash\n"
    "       ❌ Driver Error\n"
    "\n"
    "------------------------------------\n"
)


# --- Map statuses to report lines with matching emojis ---
def format_report(acc, status, emoji, balance):
    display_balance = (
        f" [💎{balance}]"
        if (status == "Success" or status == "Already Claimed")
        else ""
    )
    return f"{emoji} {acc}{display_balance}"


# Update the list comprehension to pass all 3 values from the results tuple
report_body = "\n".join(
    [format_report(acc, val[0], val[1], val[2]) for acc, val in results.items()]
)

full_message = report_header + "```\n" + report_body + "\n```"

# Fire it off!
notify_user(full_message)
