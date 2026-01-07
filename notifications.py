import telegram
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from dashboard_config import get_credentials

creds = get_credentials()
BOT_TOKEN = creds["bot_token"]

async def send_interactive_alert(channel_name, trade_data):
    """
    Sends an alert with an 'Execute Live' button if it's a Paper trade.
    """
    if not BOT_TOKEN: return
    
    chat_id = creds["channels"].get(channel_name)
    if not chat_id: return

    bot = telegram.Bot(token=BOT_TOKEN)
    
    symbol = trade_data['symbol']
    price = trade_data['entry_price']
    mode = trade_data['mode']
    
    # 5-Level Target Display
    targets_msg = "\n".join([f"🎯 T{i+1}: {t:.2f}" for i, t in enumerate(trade_data['targets'])])

    msg = (
        f"🚀 **NEW TRADE ({mode})**\n\n"
        f"Symbol: `{symbol}`\n"
        f"Entry: {price}\n"
        f"SL: {trade_data['sl']}\n\n"
        f"{targets_msg}\n"
    )

    # Add Button ONLY if it is a Paper trade (to allow Promotion)
    keyboard = None
    if mode == "PAPER":
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("⚡ Execute Live", callback_data=f"PROMOTE_{trade_data['id']}")]
        ])
    
    try:
        await bot.send_message(chat_id=chat_id, text=msg, parse_mode='Markdown', reply_markup=keyboard)
    except Exception as e:
        print(f"[TG ERROR] {e}")
