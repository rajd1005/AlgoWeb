import pandas as pd
import requests
import os
from datetime import datetime

# Cache the master list in storage to avoid re-downloading every second
CSV_PATH = os.path.join(os.getenv("RAILWAY_VOLUME_MOUNT_PATH", "."), "dhan_instruments.csv")

def update_master_list():
    """Downloads the latest Security Master List from Dhan."""
    url = "https://images.dhan.co/api/csv/scrip_master.csv"
    try:
        print("Downloading Master List...")
        df = pd.read_csv(url)
        df.to_csv(CSV_PATH, index=False)
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
        df = pd.read_csv(CSV_PATH)
        # Filter Logic
        # Note: You might need to adjust column names based on exact Dhan CSV format
        # Common columns: 'SEM_CUSTOM_SYMBOL', 'SEM_EXPIRY_DATE', 'SEM_STRIKE_PRICE'
        
        # Simple string matching for safety
        strike_str = str(strike)
        filtered = df[
            (df['SEM_TRADING_SYMBOL'].str.contains(underlying)) & 
            (df['SEM_OPTION_TYPE'] == opt_type) & 
            (df['SEM_STRIKE_PRICE'].astype(str).str.startswith(strike_str))
        ]
        
        # Sort by expiry to get nearest
        if not filtered.empty:
            # Return the first match (nearest expiry)
            row = filtered.iloc[0]
            return {
                "symbol": row['SEM_TRADING_SYMBOL'],
                "id": str(row['SEM_SMST_SECURITY_ID']),
                "exchange_segment": "NSE_FNO"
            }
    except Exception as e:
        print(f"Error finding symbol: {e}")
    
    return None
