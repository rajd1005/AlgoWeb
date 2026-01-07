import json
import os
from dhanhq import dhanhq
from dashboard_config import get_credentials

STORAGE_PATH = os.getenv("RAILWAY_VOLUME_MOUNT_PATH", ".")
TRADES_FILE = os.path.join(STORAGE_PATH, 'active_trades.json')

class StrategyManager:
    def __init__(self):
        self.creds = get_credentials()
        self.dhan = dhanhq(self.creds['client_id'], self.creds['access_token'])
        self.active_trades = self.load_trades()
        # Load Risk Settings (Default to 10 step if missing)
        self.trailing_step = 10 

    def load_trades(self):
        if os.path.exists(TRADES_FILE):
            with open(TRADES_FILE, 'r') as f:
                return json.load(f)
        return []

    def save_trades(self):
        with open(TRADES_FILE, 'w') as f:
            json.dump(self.active_trades, f, indent=4)

    def get_trade(self, trade_id):
        for t in self.active_trades:
            if str(t['id']) == str(trade_id):
                return t
        return None

    def promote_to_live(self, trade_id, qty=25):
        """
        Converts a PAPER trade to LIVE by executing a real market order.
        """
        trade = self.get_trade(trade_id)
        if not trade or trade['mode'] != "PAPER":
            return False, "Invalid Trade ID or already Live."

        try:
            # Execute REAL Order
            print(f"Executing Live Order for {trade['symbol']}...")
            self.dhan.place_order(
                security_id=trade['sec_id'],
                exchange_segment=self.dhan.NSE_FNO,
                transaction_type=self.dhan.BUY,
                quantity=qty,
                order_type=self.dhan.MARKET,
                product_type=self.dhan.INTRADAY
            )
            
            # Update Internal Record
            trade['mode'] = "LIVE"
            # Reset Entry Price to current market price? 
            # Ideally, you fetch the tradebook here. For now, we assume swift execution.
            
            self.save_trades()
            return True, f"Trade {trade['symbol']} Promoted to LIVE!"
            
        except Exception as e:
            return False, f"Execution Failed: {str(e)}"

    def place_trade(self, symbol_obj, qty, sl_points, mode="PAPER"):
        # ... (Same as before, just ensure targets use the 0.5x, 1x logic) ...
        entry_price = 0
        if mode == "LIVE":
             # ... Place Order Logic ...
             entry_price = 100.0 # Placeholder/Mock
        else:
             # Fetch LTP
             ltp_data = self.dhan.get_ltp_data({symbol_obj['exchange_segment']: [symbol_obj['id']]})
             if ltp_data['status'] == 'success':
                 entry_price = float(ltp_data['data'][symbol_obj['exchange_segment']][symbol_obj['id']])
             else:
                 entry_price = 100.0

        # 5-Level Target Logic (Exact per Doc)
        # T1: 0.5x, T2: 1.0x, T3: 1.5x, T4: 2.0x, T5: 3.0x
        targets = [
            entry_price + (sl_points * 0.5),
            entry_price + (sl_points * 1.0),
            entry_price + (sl_points * 1.5),
            entry_price + (sl_points * 2.0),
            entry_price + (sl_points * 3.0)
        ]

        trade = {
            "id": len(self.active_trades) + 1,
            "symbol": symbol_obj['symbol'],
            "sec_id": symbol_obj['id'],
            "mode": mode,
            "entry_price": entry_price,
            "sl": entry_price - sl_points,
            "targets": targets,
            "status": "OPEN",
            "max_mtm": entry_price,
            "t1_hit": False
        }
        
        self.active_trades.append(trade)
        self.save_trades()
        return trade

    def update_trades(self):
        """
        Refined Logic: T1 Safeguard + Trailing Step
        """
        for trade in self.active_trades:
            if trade['status'] != "OPEN": continue
            
            # MOCK LTP (In production, use batch fetch)
            ltp = 100.0 

            # A. T1 Safe-Guard Logic
            if ltp >= trade['targets'][0] and not trade['t1_hit']:
                trade['t1_hit'] = True
                trade['sl'] = trade['entry_price'] # Move SL to Cost
                print(f"🛡️ T1 Hit. SL Moved to Cost for {trade['symbol']}")

            # B. Trailing SL (Step Logic)
            if ltp > trade['max_mtm']:
                # Calculate how many "steps" we moved
                gain = ltp - trade['entry_price']
                # If gain crosses a multiple of step (e.g. 10, 20, 30)
                # This is a simplified trailing logic based on Max High
                diff = ltp - trade['max_mtm']
                if diff >= self.trailing_step:
                    trade['sl'] += self.trailing_step
                    trade['max_mtm'] = ltp
            
            # C. Check Exit
            if ltp <= trade['sl']:
                trade['status'] = "SL_HIT"

        self.save_trades()
