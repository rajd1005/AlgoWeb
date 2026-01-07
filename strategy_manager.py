import json
import os
from dhanhq import dhanhq
from dashboard_config import get_credentials, increment_trade_count

STORAGE_PATH = os.getenv("RAILWAY_VOLUME_MOUNT_PATH", ".")
TRADES_FILE = os.path.join(STORAGE_PATH, 'active_trades.json')

class StrategyManager:
    def __init__(self):
        creds = get_credentials()
        self.dhan = dhanhq(creds['client_id'], creds['access_token'])
        self.active_trades = self.load_trades()

    def load_trades(self):
        if os.path.exists(TRADES_FILE):
            with open(TRADES_FILE, 'r') as f:
                return json.load(f)
        return []

    def save_trades(self):
        with open(TRADES_FILE, 'w') as f:
            json.dump(self.active_trades, f, indent=4)

    def place_trade(self, symbol_obj, qty, sl_points, mode="PAPER"):
        """
        Calculates Targets and enters trade (or simulates it).
        """
        entry_price = 0
        
        if mode == "LIVE":
            try:
                # Execute Market Order
                order = self.dhan.place_order(
                    security_id=symbol_obj['id'],
                    exchange_segment=self.dhan.NSE_FNO,
                    transaction_type=self.dhan.BUY,
                    quantity=qty,
                    order_type=self.dhan.MARKET,
                    product_type=self.dhan.INTRADAY
                )
                # Fetch actual entry price (mocked here for safety, usually need order ID fetch)
                entry_price = 100.0 # Placeholder: In real code, fetch tradebook
            except Exception as e:
                return {"status": "error", "msg": str(e)}
        else:
            # Paper Trade: Fetch LTP
            ltp_data = self.dhan.get_ltp_data({symbol_obj['exchange_segment']: [symbol_obj['id']]})
            if ltp_data['status'] == 'success':
                entry_price = float(ltp_data['data'][symbol_obj['exchange_segment']][symbol_obj['id']])
            else:
                entry_price = 100.0

        # Calculate Targets (Risk 1:2, 1:3 etc)
        trade = {
            "id": len(self.active_trades) + 1,
            "symbol": symbol_obj['symbol'],
            "sec_id": symbol_obj['id'],
            "mode": mode,
            "entry_price": entry_price,
            "sl": entry_price - sl_points,
            "targets": [entry_price + (sl_points * i * 0.5) for i in range(1, 6)],
            "status": "OPEN",
            "max_mtm": entry_price
        }
        
        self.active_trades.append(trade)
        self.save_trades()
        return trade

    def update_trades(self):
        """
        Called periodically to check SL/Targets.
        """
        for trade in self.active_trades:
            if trade['status'] != "OPEN": continue

            # Fetch Live Price
            # In real usage, fetch batch LTP for efficiency
            ltp = 105.0 # Mock LTP for structure
            
            # 1. Check Target 1 Hit (Move SL to Cost)
            if ltp >= trade['targets'][0] and trade['sl'] < trade['entry_price']:
                trade['sl'] = trade['entry_price']
                print(f"Safe Guard Triggered for {trade['symbol']}")

            # 2. Trailing Logic (Simple Step)
            if ltp > trade['max_mtm']:
                diff = ltp - trade['max_mtm']
                if diff > 5: # For every 5 points move
                    trade['sl'] += 5
                    trade['max_mtm'] = ltp
            
            # 3. Check SL Hit
            if ltp <= trade['sl']:
                trade['status'] = "SL_HIT"
                # Logic to close live order here...

        self.save_trades()
