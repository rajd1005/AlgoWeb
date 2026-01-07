# filename: notifications.py
import telegram
import asyncio
from dashboard_config import get_credentials

creds = get_credentials()
BOT_TOKEN = creds["bot_token"]

async def send_telegram_alert(channel_name, trade_data, update_type="ENTRY"):
    """
    Sends alerts. 
    channel_name: 'Free' or 'VIP'
    """
    if not BOT_TOKEN: return
    
    chat_id = creds["channels"].get(channel_name)
    if not chat_id: return

    bot = telegram.Bot(token=BOT_TOKEN)
    
    symbol = trade_data['symbol']
    price = trade_data['entry_price']
    
    if update_type == "ENTRY":
        msg = (
            f"🚀 **NEW TRADE ALERT** ({channel_name})\n\n"
            f"Symbol: `{symbol}`\n"
            f"Entry: {price}\n"
            f"SL: {trade_data['sl']}\n\n"
            f"🎯 Targets:\n"
            f"1. {trade_data['targets'][0]}\n"
            f"2. {trade_data['targets'][1]}\n"
            f"3. {trade_data['targets'][2]}\n"
        )
    elif update_type == "EXIT":
        msg = f"🛑 **TRADE CLOSED**\n{symbol}\nExit Price: {trade_data['current_ltp']}"
    
    try:
        await bot.send_message(chat_id=chat_id, text=msg, parse_mode='Markdown')
    except Exception as e:
        print(f"[TG ERROR] {e}")
