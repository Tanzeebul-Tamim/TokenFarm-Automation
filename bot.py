import undetected_chromedriver as uc
import requests
from selenium.webdriver.common.by import By
from dotenv import load_dotenv
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import os

# --- CONFIGURATION ---
# Load the variables from the .env file
load_dotenv()

BASE_PATH = os.path.expanduser(os.getenv("BASE_PATH")) # your hidden profiles folder
URL = os.getenv("CLAIM_URL") # website url
TOKEN=os.getenv("BOT_FATHER_TOKEN") # your BotFather token here
ID=os.getenv("USER_INFO_BOT_ID") # your UserInfoBot ID here 

# Automatically get all folder names inside that directory
# We skip hidden files (starting with '.') and common system files
ACCOUNTS = [
    f for f in os.listdir(BASE_PATH) 
    if os.path.isdir(os.path.join(BASE_PATH, f)) and not f.startswith('.')
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

#-------------------------------------------------

# Define the main function
def run_farm(acc_name):
    print(f"\n🚀 Starting harvest for: {acc_name}")
    
    options = uc.ChromeOptions()
    options.add_argument(f"--user-data-dir={os.path.join(BASE_PATH, acc_name)}")
    
    # Running 'headless' makes it invisible (no windows pop up). 
    options.add_argument("--headless")
    
    driver = uc.Chrome(options=options, version_main=143)
    status = "Failed"

    try:
        driver.get(URL)
        
        # Give the site 8 seconds to load cookies and clear the 'Sign In' flash
        time.sleep(8)
        
        # Check if we are logged out
        login_check = driver.find_elements(By.XPATH, "//*[contains(translate(text(), 'SIGN', 'sign'), 'sign in')]")
        if len(login_check) > 0:
            notify_user(f"*❌ {acc_name}:*\nLogged out. Skipping.")
            status = "Logged Out"
        else:
            # Look for the Claim button
            wait = WebDriverWait(driver, 15)
            # This looks for a button that contains 'Claim' AND has the specific 'indigo-600' class
            claim_btn = wait.until(EC.element_to_be_clickable((
                By.XPATH, "//button[contains(@class, 'bg-indigo-600') and contains(., 'Claim')]"
            )))
            
            claim_btn.click()
            notify_user(f"*✅ {acc_name}:*\nTokens claimed!")
            status = "Success"
            time.sleep(3) # Let the site save the click
            
    except Exception:
        notify_user(f"*ℹ️ {acc_name}:*\nTokens already claimed for today.")
        status = "Already Claimed"
    
    driver.quit()
    return status

# --- THE MAIN LOOP ---
results = {}

notify_user(f"*🚜 STARTING THE TOKEN FARM...*\n📂 Found _{len(ACCOUNTS)}_ accounts in the vault")

for acc in ACCOUNTS:
    result = run_farm(acc)
    results[acc] = result
    print(f"--- 💤 Resting for 15s to stay under the radar ---")
    time.sleep(15)

# --- THE FINAL REPORT ---

# Create the message content
report_header = f"📋 *Report Summary:\n*🚜 Harvested {len(ACCOUNTS)} Accounts\n"
report_body = "\n\n".join([
    f"✅ {acc}:\nSuccess" if status == "Success" else f"❌ {acc}:\n{status}"
    for acc, status in results.items()
])
full_message = report_header + "```\n" + report_body + "\n```"

# Fire it off!
notify_user(full_message)