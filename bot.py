import os
import asyncio
import aiohttp
from telegram import Bot, Update
from telegram.ext import Application, CommandHandler, ContextTypes

BOT_TOKEN = os.environ.get("BOT_TOKEN")
CHAT_ID = os.environ.get("CHAT_ID")

# ===== COMMANDS =====

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎯 AlphaSniper Bot — Token Spotter\n\n"
        "أنا شايل عينك على ETH و BSC 24/7\n\n"
        "الأوامر:\n"
        "/new_tokens — آخر التوكنات الجديدة\n"
        "/scan [عنوان] — فحص توكن معين\n"
        "/status — حالة البوت"
    )

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "✅ البوت شغال\n"
        "🔍 يراقب: ETH + BSC\n"
        "⏱ Real-time alerts: مفعّل"
    )

async def new_tokens(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🔍 جاري جلب آخر التوكنات...")
    tokens = await fetch_new_tokens()
    if not tokens:
        await update.message.reply_text("⚠️ ما لقيت توكنات هلق، حاول بعد شوي.")
        return
    for token in tokens[:3]:
        msg = format_token_alert(token)
        await update.message.reply_text(msg, disable_web_page_preview=True)

async def scan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ مثال: /scan 0x123...")
        return
    address = context.args[0]
    await update.message.reply_text(f"🔬 جاري فحص {address[:10]}...")
    result = await check_honeypot(address)
    await update.message.reply_text(result)

# ===== DATA =====

async def fetch_new_tokens():
    try:
        async with aiohttp.ClientSession() as session:
            url = "https://api.dexscreener.com/token-boosts/latest/v1"
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data[:5] if isinstance(data, list) else []
    except Exception as e:
        print(f"Error: {e}")
    return []

async def check_honeypot(address: str):
    try:
        async with aiohttp.ClientSession() as session:
            url = f"https://api.honeypot.is/v2/IsHoneypot?address={address}&chainID=1"
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    hp = data.get("honeypotResult", {})
                    sim = data.get("simulationResult", {})
                    is_hp = hp.get("isHoneypot", False)
                    buy_tax = sim.get("buyTax", "?")
                    sell_tax = sim.get("sellTax", "?")
                    if is_hp:
                        return f"🔴 HONEYPOT!\nالعنوان: {address[:20]}...\nBuy Tax: {buy_tax}%\nSell Tax: {sell_tax}%"
                    else:
                        return f"🟢 التوكن نظيف\nالعنوان: {address[:20]}...\nBuy Tax: {buy_tax}%\nSell Tax: {sell_tax}%"
    except Exception as e:
        print(f"Error: {e}")
    return "⚠️ ما قدرت أفحص هاد العنوان."

def format_token_alert(token: dict) -> str:
    name = token.get("description", "Unknown")
    address = token.get("tokenAddress", "")
    chain = token.get("chainId", "").upper()
    url = token.get("url", "")
    return (
        f"🚨 توكن جديد — {chain}\n\n"
        f"{name}\n"
        f"العنوان: {address[:20]}...\n\n"
        f"🔍 {url}"
    )

# ===== MONITOR =====

async def monitor_new_tokens(bot: Bot):
    seen = set()
    print("🔍 بدأ المراقبة...")
    while True:
        try:
            tokens = await fetch_new_tokens()
            for token in tokens:
                addr = token.get("tokenAddress", "")
                chain = token.get("chainId", "")
                if addr and addr not in seen and chain in ["ethereum", "bsc"]:
                    seen.add(addr)
                    msg = format_token_alert(token)
                    await bot.send_message(
                        chat_id=CHAT_ID,
                        text=msg,
                        disable_web_page_preview=True
                    )
                    print(f"✅ Alert: {addr[:10]}")
        except Exception as e:
            print(f"Monitor error: {e}")
        await asyncio.sleep(60)

# ===== MAIN =====

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("new_tokens", new_tokens))
    app.add_handler(CommandHandler("scan", scan))

    async def post_init(application: Application):
        asyncio.create_task(monitor_new_tokens(application.bot))

    app.post_init = post_init
    print("🚀 AlphaSniper Bot شغال!")
    app.run_polling()

if __name__ == "__main__":
    main()
