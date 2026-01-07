import json
import os
from datetime import datetime

# --- RAILWAY PERSISTENCE SETUP ---
# Railway Volumes should be mounted to /app/storage (or defined in env)
STORAGE_PATH = os.getenv("RAILWAY_VOLUME_MOUNT_PATH", ".")
CONFIG_FILE = os.path.join(STORAGE_PATH, 'bot_config.json')

# Default template if variables are missing
DEFAULT_CONFIG = {
    "daily_stats": {"trade_count": 0, "last_reset_date": datetime.now().strftime("%Y-%m-%d")}
}

def load_config():
    """
    Loads config from Volume. If missing, creates a basic one.
    Credentials are fetched from ENV VARS, not the file, for security.
    """
    # 1. Load Persistence (Stats/State)
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
        except:
            config = DEFAULT_CONFIG
    else:
        config = DEFAULT_CONFIG
        save_config(config)

    # 2. Reset Daily Stats if New Day
    today = datetime.now().strftime("%Y-%m-%d")
    if config["daily_stats"].get("last_reset_date") != today:
        config["daily_stats"] = {"trade_count": 0, "last_reset_date": today}
        save_config(config)

    return config

def get_credentials():
    """
    Fetches API Keys from Railway Environment Variables.
    """
    return {
        "client_id": os.getenv("DHAN_CLIENT_ID", ""),
        "access_token": os.getenv("DHAN_ACCESS_TOKEN", ""),
        "bot_token": os.getenv("TG_BOT_TOKEN", ""),
        "channels": {
            "Free": os.getenv("TG_FREE_ID", ""),
            "VIP": os.getenv("TG_VIP_ID", "")
        }
    }

def save_config(config_data):
    try:
        os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
        with open(CONFIG_FILE, 'w') as f:
            json.dump(config_data, f, indent=4)
    except Exception as e:
        print(f"[ERROR] Save Config Failed: {e}")

def check_restriction(requested_channel):
    """
    Logic: If 'Free' requested but limit (1) reached -> Force 'VIP'.
    """
    config = load_config()
    stats = config.get("daily_stats", {})
    
    if requested_channel == "Free":
        if stats.get("trade_count", 0) >= 1:
            return "VIP" # Restriction applied
    return requested_channel

def increment_trade_count():
    config = load_config()
    config["daily_stats"]["trade_count"] += 1
    save_config(config)
