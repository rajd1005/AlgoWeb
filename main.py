import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, CallbackQueryHandler
from dashboard_config import get_credentials, check_restriction, increment_trade_count
from strategy_manager import StrategyManager
from smart_trader import find_option_symbol, get_atm_strike, update_master_list
from notifications import send_interactive_alert

logging.basicConfig(level=logging.INFO)
creds = get_credentials()
manager = StrategyManager()

# ... (start command same as before) ...

async def buy_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # ... (Command parsing same as before) ...
    try:
        args = context.args
        index = args[0].upper()
        opt_type = args[1].upper()
        sl = float(args[2])
        mode = args[3].upper()

        # Mock LTP for finding strike (Replace with real fetch)
        ltp = 24100 
        atm = get_atm_strike(ltp)
        symbol_obj = find_option_symbol(index, "Current", atm, opt_type)
        
        if not symbol_obj:
            await update.message.reply_text("❌ Symbol not found.")
            return

        # Execute
        trade = manager.place_trade(symbol_obj, 25, sl, mode)
        
        # Restriction Check
        target_channel = check_restriction("Free")
        if target_channel == "VIP":
             await update.message.reply_text("⚠️ Limit reached. Sending to VIP.")

        # Send Interactive Alert
        await send_interactive_alert(target_channel, trade)
        increment_trade_count()
        
        await update.message.reply_text(f"✅ Trade Placed: {trade['symbol']}")

    except Exception as e:
        await update.message.reply_text(f"Error: {e}")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handles clicks on 'Execute Live' buttons.
    """
    query = update.callback_query
    await query.answer() # Ack the click
    
    data = query.data
    if data.startswith("PROMOTE_"):
        trade_id = data.split("_")[1]
        
        success, msg = manager.promote_to_live(trade_id)
        
        if success:
            await query.edit_message_text(text=f"{query.message.text}\n\n✅ **PROMOTED TO LIVE**")
            await context.bot.send_message(chat_id=query.message.chat_id, text=f"🚀 {msg}")
        else:
            await context.bot.send_message(chat_id=query.message.chat_id, text=f"⚠️ {msg}")

if __name__ == '__main__':
    update_master_list()
    
    application = ApplicationBuilder().token(creds['bot_token']).build()
    
    application.add_handler(CommandHandler('start', start)) # Define start func
    application.add_handler(CommandHandler('buy', buy_command))
    # NEW: Handle Button Clicks
    application.add_handler(CallbackQueryHandler(button_handler))
    
    print("Bot is Polling...")
    application.run_polling()
