import pandas as pd
import requests
import os
import io

# STORAGE_PATH is defined by Railway. If running locally, use current folder (.)
STORAGE_PATH = os.getenv("RAILWAY_VOLUME_MOUNT_PATH", ".")
CSV_PATH = os.path.join(STORAGE_PATH, "dhan_instruments.csv")

def update_master_list():
    """Downloads the latest Security Master List from Dhan with Anti-Bot headers."""
    url = "https://images.dhan.co/api/csv/scrip_master.csv"
    
    # MIMIC REAL BROWSER HEADERS (Crucial for Railway)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Referer": "https://dhan.co/"
    }

    try:
        print("Downloading Master List...")
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status() # Check for 403/404 errors
        
        # Save to file
        with open(CSV_PATH, 'wb') as f:
            f.write(response.content)
            
        print("✅ Master List Updated Successfully.")
    except Exception as e:
        print(f"⚠️ Failed to download Master List: {e}")
        print("Attempting to use existing file if available...")

def get_atm_strike(ltp, step=50):
    return round(ltp / step) * step

def find_option_symbol(underlying, expiry_month_legacy, strike, opt_type):
    # If the file doesn't exist, try downloading one last time
    if not os.path.exists(CSV_PATH):
        update_master_list()
        
    try:
        # Load CSV (low_memory=False to avoid warnings)
        if os.path.exists(CSV_PATH):
            df = pd.read_csv(CSV_PATH, low_memory=False)
            
            strike_str = str(strike)
            # Filter Logic
            filtered = df[
                (df['SEM_TRADING_SYMBOL'].str.contains(underlying, na=False)) & 
                (df['SEM_OPTION_TYPE'] == opt_type) & 
                (df['SEM_STRIKE_PRICE'].astype(str).str.startswith(strike_str))
            ]
            
            if not filtered.empty:
                row = filtered.iloc[0]
                return {
                    "symbol": row['SEM_TRADING_SYMBOL'],
                    "id": str(row['SEM_SMST_SECURITY_ID']),
                    "exchange_segment": "NSE_FNO"
                }
        else:
            print("❌ Error: Master List CSV not found.")
            return None

    except Exception as e:
        print(f"Error finding symbol: {e}")
    
    return None
