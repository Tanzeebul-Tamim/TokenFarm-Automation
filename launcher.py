import undetected_chromedriver as uc
import os
import time
import random
from dotenv import load_dotenv

# --- 1. SETUP & CONFIG ---
load_dotenv()

BASE_PATH = os.path.expanduser(os.getenv("BASE_PATH"))
URL = os.getenv("CLAIM_URL")

ACCOUNTS = [
    f for f in os.listdir(BASE_PATH)
    if os.path.isdir(os.path.join(BASE_PATH, f)) and not f.startswith(".")
]
ACCOUNTS.sort()

# We store the drivers in a list so Python doesn't "garbage collect" (close) them
drivers = []

# --- 2. THE LAUNCHER FUNCTION ---
def launch_profile(acc_name):
    print(f"🖥️  Launching Profile: {acc_name}...")
    
    options = uc.ChromeOptions()
    options.add_argument(f"--user-data-dir={os.path.join(BASE_PATH, acc_name)}")
    
    # Set size and random position
    options.add_argument("--window-size=900,700")
    x_pos = random.randint(50, 400)
    y_pos = random.randint(50, 300)
    options.add_argument(f"--window-position={x_pos},{y_pos}")

    try:
        # Launching without the "detach" option to avoid the error
        driver = uc.Chrome(options=options, version_main=143)
        driver.get(URL)
        drivers.append(driver) # Store it to keep it alive
        print(f"✅ {acc_name} is active.")
    except Exception as e:
        print(f"❌ Failed to launch {acc_name}: {e}")

# --- 3. THE EXECUTION ---
if __name__ == "__main__":
    print(f"🚀 PROFILE MANAGER: Opening {len(ACCOUNTS)} windows...")
    print("⚠️  Keep this terminal open to keep the browsers open!")
    print("-" * 40)

    try:
        for acc in ACCOUNTS:
            launch_profile(acc)
            time.sleep(2.5) # Space out the launches for RAM safety

        print("\n✨ All profiles launched!")
        print("🔒 Script is now 'Idling' to keep browsers alive. Press Ctrl+C to close all windows.")
        
        # This loop keeps the script running so the browsers don't close
        while True:
            time.sleep(10)

    except KeyboardInterrupt:
        print("\n🛑 Closing all windows and exiting...")
        for driver in drivers:
            try:
                driver.quit()
            except:
                pass