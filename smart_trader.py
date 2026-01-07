import pandas as pd
import requests
import os
import time

# STORAGE_PATH is defined by Railway. If running locally, use current folder (.)
STORAGE_PATH = os.getenv("RAILWAY_VOLUME_MOUNT_PATH", ".")
CSV_PATH = os.path.join(STORAGE_PATH, "dhan_instruments.csv")

# --- CORRECT V2 URLS FROM DOCUMENTATION ---
# Compact List (Faster, contains essential fields)
URL_COMPACT = "https://images.dhan.co/api-data/api-scrip-master.csv"
# Detailed List (Use only if Compact fails)
URL_DETAILED = "https://images.dhan.co/api-data/api-scrip-master-detailed.csv"

def update_master_list():
    """Downloads the latest Security Master List using the correct v2 URL."""
    
    # Headers are required to mimic a real browser and avoid 403 Forbidden
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive"
    }

    print(f"⬇️ Downloading Master List from v2 API...")
    
    try:
        # Try Compact List First (Preferred)
        response = requests.get(URL_COMPACT, headers=headers, timeout=15)
        response.raise_for_status()
        
        with open(CSV_PATH, 'wb') as f:
            f.write(response.content)
        print("✅ Master List Updated (Compact Version).")
        return True

    except Exception as e:
        print(f"⚠️ Compact download failed: {e}. Retrying with Detailed List...")
        
        try:
            # Fallback to Detailed List
            response = requests.get(URL_DETAILED, headers=headers, timeout=30)
            response.raise_for_status()
            
            with open(CSV_PATH, 'wb') as f:
                f.write(response.content)
            print("✅ Master List Updated (Detailed Version).")
            return True
            
        except Exception as e2:
            print(f"❌ CRITICAL: Failed to download Master List. {e2}")
            return False

def get_atm_strike(ltp, step=50):
    return round(ltp / step) * step

def find_option_symbol(underlying, expiry_month_legacy, strike, opt_type):
    """
    Search the CSV for the specific Security ID.
    Note: v2 CSV Column names might differ slightly, this logic handles standard mapping.
    """
    if not os.path.exists(CSV_PATH):
        success = update_master_list()
        if not success: return None
        
    try:
        # Load CSV
        # usecols helps reduce memory usage on Railway
        try:
            df = pd.read_csv(CSV_PATH, low_memory=False)
        except:
            # If CSV is corrupt, re-download
            update_master_list()
            df = pd.read_csv(CSV_PATH, low_memory=False)
        
        # Standardize Columns (The v2 CSV uses specific headers)
        # We need: SEM_TRADING_SYMBOL, SEM_OPTION_TYPE, SEM_STRIKE_PRICE, SEM_SMST_SECURITY_ID
        
        strike_str = str(strike)
        
        # Filtering Logic
        filtered = df[
            (df['SEM_TRADING_SYMBOL'].str.contains(underlying, na=False)) & 
            (df['SEM_OPTION_TYPE'] == opt_type) & 
            (df['SEM_STRIKE_PRICE'].astype(str).str.startswith(strike_str))
        ]
        
        # Sort by Expiry (SEM_EXPIRY_DATE) to get the nearest one
        # If expiry column exists, sort. If not, take first match.
        if 'SEM_EXPIRY_DATE' in df.columns:
            filtered = filtered.sort_values(by='SEM_EXPIRY_DATE')

        if not filtered.empty:
            row = filtered.iloc[0]
            return {
                "symbol": row['SEM_TRADING_SYMBOL'],
                "id": str(row['SEM_SMST_SECURITY_ID']),
                "exchange_segment": "NSE_FNO"
            }
            
    except Exception as e:
        print(f"Error finding symbol in CSV: {e}")
    
    return None
