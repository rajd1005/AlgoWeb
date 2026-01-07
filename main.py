import logging
import asyncio
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler
from dashboard_config import get_credentials, check_restriction, increment_trade_count
from strategy_manager import StrategyManager
from smart_trader import find_option_symbol, get_atm_strike, update_master_list
from notifications import send_telegram_alert

# Setup Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

creds = get_credentials()
manager = StrategyManager()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 AlgoBot Active on Railway!\n\n"
        "Commands:\n"
        "/buy <NIFTY/BANKNIFTY> <CE/PE> <SL_PTS> <MODE>\n"
        "/status - Show Open Trades\n"
        "/update_master - Refresh Dhan CSV"
    )

async def buy_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Usage: /buy NIFTY CE 20 PAPER
    """
    try:
        args = context.args
        if len(args) < 4:
            await update.message.reply_text("Usage: /buy NIFTY CE 20 PAPER")
            return

        index = args[0].upper()
        opt_type = args[1].upper()
        sl = float(args[2])
        mode = args[3].upper() # PAPER or LIVE

        # 1. Get LTP (Mocked here, use manager.dhan.get_ltp in prod)
        ltp = 24120 # Example
        atm = get_atm_strike(ltp)
        
        # 2. Find Symbol
        symbol_obj = find_option_symbol(index, "Current", atm, opt_type)
        
        if not symbol_obj:
            await update.message.reply_text("❌ Could not find Option Symbol in Master List.")
            return

        # 3. Place Trade
        trade = manager.place_trade(symbol_obj, 25, sl, mode)
        
        # 4. Handle Notification Restrictions
        target_channel = check_restriction("Free") # Default request to Free
        if target_channel == "VIP" and mode == "LIVE":
             await update.message.reply_text("⚠️ Free Limit Reached. Posting to VIP.")

        # 5. Send Alert
        await send_telegram_alert(target_channel, trade)
        increment_trade_count()
        
        await update.message.reply_text(f"✅ Trade Executed ({mode}): {symbol_obj['symbol']}")

    except Exception as e:
        await update.message.reply_text(f"Error: {e}")

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    trades = manager.active_trades
    open_trades = [t for t in trades if t['status'] == "OPEN"]
    msg = f"Open Trades: {len(open_trades)}\n"
    for t in open_trades:
        msg += f"{t['symbol']} | P/L: {t['entry_price']} -> Live\n"
    await update.message.reply_text(msg)

if __name__ == '__main__':
    # Initial Setup
    update_master_list()
    
    # Run Bot
    application = ApplicationBuilder().token(creds['bot_token']).build()
    
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('buy', buy_command))
    application.add_handler(CommandHandler('status', status))
    
    print("Bot is Polling...")
    application.run_polling()
