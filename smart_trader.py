import pandas as pd
import requests
import os

# Cache the master list in storage to avoid re-downloading every second
STORAGE_PATH = os.getenv("RAILWAY_VOLUME_MOUNT_PATH", ".")
CSV_PATH = os.path.join(STORAGE_PATH, "dhan_instruments.csv")

def update_master_list():
    """Downloads the latest Security Master List from Dhan."""
    url = "https://images.dhan.co/api/csv/scrip_master.csv"
    
    # FIX ADDED HERE: Headers to mimic a real browser
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        print("Downloading Master List...")
        response = requests.get(url, headers=headers)
        response.raise_for_status() # Raises error if 403 or 404
        
        with open(CSV_PATH, 'wb') as f:
            f.write(response.content)
            
        print("Master List Updated.")
    except Exception as e:
        print(f"Failed to download Master List: {e}")

def get_atm_strike(ltp, step=50):
    """Calculates ATM strike (e.g., 24130 -> 24150)."""
    return round(ltp / step) * step

def find_option_symbol(underlying, expiry_month_legacy, strike, opt_type):
    """
    Search the CSV for the specific Security ID.
    underlying: 'NIFTY'
    strike: 24500
    opt_type: 'CE' or 'PE'
    """
    if not os.path.exists(CSV_PATH):
        update_master_list()
        
    try:
        # Load CSV (Low memory mode to prevent crashing small servers)
        df = pd.read_csv(CSV_PATH, low_memory=False)
        
        # Simple string matching
        strike_str = str(strike)
        
        # Filter: Symbol matches AND Option Type matches AND Strike matches
        filtered = df[
            (df['SEM_TRADING_SYMBOL'].str.contains(underlying, na=False)) & 
            (df['SEM_OPTION_TYPE'] == opt_type) & 
            (df['SEM_STRIKE_PRICE'].astype(str).str.startswith(strike_str))
        ]
        
        # Sort by expiry to get nearest
        if not filtered.empty:
            row = filtered.iloc[0]
            return {
                "symbol": row['SEM_TRADING_SYMBOL'],
                "id": str(row['SEM_SMST_SECURITY_ID']),
                "exchange_segment": "NSE_FNO"
            }
    except Exception as e:
        print(f"Error finding symbol: {e}")
    
    return None
