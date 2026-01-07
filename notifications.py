import telegram
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from dashboard_config import get_credentials

creds = get_credentials()
BOT_TOKEN = creds["bot_token"]

async def send_telegram_alert(channel_name, trade_data, update_type="ENTRY"):
    """
    Standard text-based alert (Used for Exits/Updates).
    Restored this function to fix the ImportError.
    """
    if not BOT_TOKEN: return
    
    chat_id = creds["channels"].get(channel_name)
    if not chat_id: return

    bot = telegram.Bot(token=BOT_TOKEN)
    
    symbol = trade_data['symbol']
    
    if update_type == "ENTRY":
        msg = f"🚀 **ENTRY**: {symbol}\nPrice: {trade_data['entry_price']}"
    elif update_type == "EXIT":
        msg = f"🛑 **CLOSED**: {symbol}\nExit Price: {trade_data.get('current_ltp', 'N/A')}"
    else:
        msg = f"ℹ️ **UPDATE**: {symbol} ({update_type})"
    
    try:
        await bot.send_message(chat_id=chat_id, text=msg, parse_mode='Markdown')
    except Exception as e:
        print(f"[TG ERROR] {e}")

async def send_interactive_alert(channel_name, trade_data):
    """
    Rich alert with 'Execute Live' buttons (Used for New Entries).
    """
    if not BOT_TOKEN: return
    
    chat_id = creds["channels"].get(channel_name)
    if not chat_id: return

    bot = telegram.Bot(token=BOT_TOKEN)
    
    symbol = trade_data['symbol']
    price = trade_data['entry_price']
    mode = trade_data['mode']
    
    # Format 5 Targets
    targets_msg = "\n".join([f"🎯 T{i+1}: {t:.2f}" for i, t in enumerate(trade_data['targets'])])

    msg = (
        f"🚀 **NEW TRADE ({mode})**\n\n"
        f"Symbol: `{symbol}`\n"
        f"Entry: {price}\n"
        f"SL: {trade_data['sl']}\n\n"
        f"{targets_msg}\n"
    )

    # Add Button ONLY if it is a Paper trade
    keyboard = None
    if mode == "PAPER":
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("⚡ Execute Live", callback_data=f"PROMOTE_{trade_data['id']}")]
        ])
    
    try:
        await bot.send_message(chat_id=chat_id, text=msg, parse_mode='Markdown', reply_markup=keyboard)
    except Exception as e:
        print(f"[TG ERROR] {e}")
