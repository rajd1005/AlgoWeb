import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler
from dashboard_config import get_credentials, check_restriction, increment_trade_count
from strategy_manager import StrategyManager
from smart_trader import find_option_symbol, get_atm_strike, update_master_list
from notifications import send_interactive_alert, send_telegram_alert

# Setup Logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

creds = get_credentials()
manager = StrategyManager()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Standard Welcome Message
    """
    await update.message.reply_text(
        "🤖 **AlgoBot Active on Railway!**\n\n"
        "**Commands:**\n"
        "`/buy <INDEX> <TYPE> <SL> <MODE>`\n"
        "Ex: `/buy NIFTY CE 20 PAPER`\n\n"
        "`/status` - Show Open Trades\n"
        "`/update_master` - Refresh Dhan CSV",
        parse_mode='Markdown'
    )

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Shows all open trades and their P/L
    """
    trades = manager.active_trades
    open_trades = [t for t in trades if t['status'] == "OPEN"]
    
    if not open_trades:
        await update.message.reply_text("✅ No Open Trades.")
        return

    msg = f"📊 **Open Trades ({len(open_trades)})**\n\n"
    for t in open_trades:
        msg += f"🔹 **{t['symbol']}**\n   Entry: {t['entry_price']} | SL: {t['sl']}\n   Mode: {t['mode']}\n\n"
    
    await update.message.reply_text(msg, parse_mode='Markdown')

async def buy_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Format: /buy NIFTY CE 20 PAPER
    """
    try:
        args = context.args
        if len(args) < 4:
            await update.message.reply_text("❌ Usage: `/buy NIFTY CE 20 PAPER`", parse_mode='Markdown')
            return

        index = args[0].upper()
        opt_type = args[1].upper()
        sl_points = float(args[2])
        mode = args[3].upper() # PAPER or LIVE

        await update.message.reply_text(f"🔍 Searching for ATM {index} {opt_type}...")

        # 1. Get Mock LTP (Replace with real `dhan.get_ltp` in production)
        # For NIFTY we assume around 24100, BANKNIFTY around 51000
        mock_ltp = 24120 if index == "NIFTY" else 51500
        atm_strike = get_atm_strike(mock_ltp, step=50 if index == "NIFTY" else 100)
        
        # 2. Find Symbol in CSV
        symbol_obj = find_option_symbol(index, "Current", atm_strike, opt_type)
        
        if not symbol_obj:
            await update.message.reply_text("❌ Could not find Option Symbol in Master List.")
            return

        # 3. Place Trade
        trade = manager.place_trade(symbol_obj, 25, sl_points, mode)
        
        # 4. Handle Notification Restrictions
        target_channel = check_restriction("Free") # Default to Free
        if target_channel == "VIP" and mode == "LIVE":
             await update.message.reply_text("⚠️ Daily Limit Reached. Alert sent to VIP Channel.")

        # 5. Send Interactive Alert (With Button)
        await send_interactive_alert(target_channel, trade)
        increment_trade_count()
        
        await update.message.reply_text(f"✅ **Trade Executed!**\n{symbol_obj['symbol']}", parse_mode='Markdown')

    except Exception as e:
        logging.error(f"Buy Error: {e}")
        await update.message.reply_text(f"Error: {e}")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handles 'Execute Live' button clicks
    """
    query = update.callback_query
    await query.answer() # Acknowledge the click immediately
    
    data = query.data
    
    if data.startswith("PROMOTE_"):
        trade_id = data.split("_")[1]
        
        # Execute the Promotion Logic
        success, msg = manager.promote_to_live(trade_id)
        
        if success:
            # Update the message to remove the button and show success
            await query.edit_message_text(text=f"{query.message.text}\n\n✅ **PROMOTED TO LIVE**", parse_mode='Markdown')
            await context.bot.send_message(chat_id=query.message.chat_id, text=f"🚀 {msg}")
        else:
            await context.bot.send_message(chat_id=query.message.chat_id, text=f"⚠️ {msg}")

async def manual_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Force update master list"""
    await update.message.reply_text("⬇️ Updating Master List...")
    update_master_list()
    await update.message.reply_text("✅ Update Complete.")

if __name__ == '__main__':
    # Initial Setup
    print("🤖 Bot Starting...")
    update_master_list()
    
    # Run Bot
    if not creds['bot_token']:
        print("❌ ERROR: TG_BOT_TOKEN is missing.")
    else:
        application = ApplicationBuilder().token(creds['bot_token']).build()
        
        # Register Commands
        application.add_handler(CommandHandler('start', start))
        application.add_handler(CommandHandler('buy', buy_command))
        application.add_handler(CommandHandler('status', status))
        application.add_handler(CommandHandler('update_master', manual_update))
        
        # Register Button Handler
        application.add_handler(CallbackQueryHandler(button_handler))
        
        print("✅ Bot is Polling...")
        application.run_polling()
